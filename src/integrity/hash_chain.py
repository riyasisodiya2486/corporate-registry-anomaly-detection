import hashlib
import os

from sqlalchemy import create_engine, text


def compute_record_hash(entity_row, previous_hash: str) -> str:
    """
    entity_row: dict-like with keys cin, company_name_normalized,
    address_normalized, authorized_capital, company_status

    previous_hash: the record_hash of the row before this one
    ('' for the first record)
    """
    payload = (
        f"{entity_row['cin']}|{entity_row['company_name_normalized']}|"
        f"{entity_row['address_normalized']}|{entity_row['authorized_capital']}|"
        f"{entity_row['company_status']}|{previous_hash}"
    )

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_all_entities(engine):
    """Build the hash chain over all cleaned entities using batched inserts.

    ``engine`` must be a SQLAlchemy engine connected to the target database.
    The function truncates ``record_hashes`` before rebuilding the chain, so
    callers are responsible for ensuring this is the intended target.
    """

    BATCH_SIZE = 500

    with engine.connect() as conn:

        rows = conn.execute(text("""
            SELECT entity_id, cin, company_name_normalized,
                   address_normalized, authorized_capital, company_status
            FROM cleaned_entities
            ORDER BY entity_id
        """)).mappings().all()

        # Always start with exactly one fresh chain.
        conn.execute(text("TRUNCATE TABLE record_hashes RESTART IDENTITY"))
        conn.commit()

        previous_hash = ""
        batch = []
        count = 0

        for row in rows:

            record_hash = compute_record_hash(
                row,
                previous_hash
            )

            batch.append({
                "eid": row["entity_id"],
                "rh": record_hash,
                "ph": previous_hash
            })

            previous_hash = record_hash
            count += 1

            if len(batch) == BATCH_SIZE:

                conn.execute(
                    text("""
                        INSERT INTO record_hashes
                            (entity_id, record_hash, previous_hash)
                        VALUES
                            (:eid, :rh, :ph)
                    """),
                    batch
                )

                conn.commit()

                print(
                    f"Inserted {count:,}/{len(rows):,} hash records"
                )

                batch = []

        # Insert remaining records
        if batch:

            conn.execute(
                text("""
                    INSERT INTO record_hashes
                        (entity_id, record_hash, previous_hash)
                    VALUES
                        (:eid, :rh, :ph)
                """),
                batch
            )

            conn.commit()

        print(
            f"SUCCESS: hash-chained {count:,} entity records"
        )


AUDIT_CHAIN_LOCK_ID = 0x43524144


def acquire_audit_chain_lock(connection) -> None:
    """Serialize audit-chain writers for the duration of their transaction.

    PostgreSQL transaction-level advisory locks are released automatically on
    commit or rollback. Every writer using this module must acquire this lock
    before reading the current tail of audit_log.
    """
    connection.execute(
        text("SELECT pg_advisory_xact_lock(:lock_id)"),
        {"lock_id": AUDIT_CHAIN_LOCK_ID},
    )


def _write_audit_action(connection, action_type: str, cluster_id, reviewer: str) -> str:
    acquire_audit_chain_lock(connection)
    last = connection.execute(
        text(
            "SELECT action_hash FROM audit_log "
            "ORDER BY log_id DESC LIMIT 1"
        )
    ).fetchone()
    previous_hash = last[0] if last else ""

    import datetime

    timestamp = datetime.datetime.now()
    action_hash = compute_audit_action_hash(
        action_type, cluster_id, reviewer, timestamp, previous_hash
    )

    connection.execute(
        text("""
            INSERT INTO audit_log
            (action_type, cluster_id, reviewer, created_at, action_hash, previous_hash)
            VALUES
            (:at, :cid, :rev, :created_at, :ah, :ph)
        """),
        {
            "at": action_type,
            "cid": cluster_id,
            "rev": reviewer,
            "created_at": timestamp,
            "ah": action_hash,
            "ph": previous_hash,
        },
    )
    return action_hash


def log_audit_action(
    action_type: str,
    cluster_id,
    reviewer: str,
    db_engine=None,
    connection=None,
) -> str:
    """Write one chained audit row to ``audit_log``.

    Exactly one of ``db_engine`` or ``connection`` must be supplied. There is
    no module-level default engine: passing neither raises ``ValueError`` so a
    misconfiguration cannot silently target an unintended database.

    ``db_engine`` opens its own transaction. Callers that need an atomic
    multi-statement operation may pass their active ``connection``; in that
    case the caller owns commit/rollback.
    """
    if connection is not None:
        if db_engine is not None:
            raise ValueError("Pass either connection or db_engine, not both")
        return _write_audit_action(connection, action_type, cluster_id, reviewer)

    if db_engine is None:
        raise ValueError(
            "log_audit_action requires either db_engine= or connection=; "
            "no default engine is available"
        )
    with db_engine.begin() as conn:
        return _write_audit_action(conn, action_type, cluster_id, reviewer)


def compute_audit_action_hash(
    action_type: str,
    cluster_id,
    reviewer: str,
    timestamp,
    previous_hash: str,
) -> str:
    """Hash audit fields using the exact serialization used by insertion."""
    timestamp_text = timestamp if isinstance(timestamp, str) else timestamp.isoformat()
    payload = f"{action_type}|{cluster_id}|{reviewer}|{timestamp_text}|{previous_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_audit_chain_rows(rows):
    """Verify ordered audit rows without database access or mutation.

    Returns a result dictionary with ``valid``, ``count``, and, on failure,
    the first invalid ``log_id`` and a concise ``reason``.
    """
    expected_previous = ""
    count = 0
    for row in rows:
        log_id = row["log_id"]
        if row["previous_hash"] != expected_previous:
            return {
                "valid": False,
                "count": count + 1,
                "log_id": log_id,
                "reason": "previous_hash does not match the preceding action_hash",
            }

        timestamp = row["created_at"]
        if timestamp is None:
            return {
                "valid": False,
                "count": count + 1,
                "log_id": log_id,
                "reason": "created_at is missing; the action hash cannot be recomputed",
            }
        try:
            expected_hash = compute_audit_action_hash(
                row["action_type"],
                row["cluster_id"],
                row["reviewer"],
                timestamp,
                expected_previous,
            )
        except (AttributeError, TypeError, ValueError) as error:
            return {
                "valid": False,
                "count": count + 1,
                "log_id": log_id,
                "reason": f"created_at cannot be serialized: {error}",
            }
        if row["action_hash"] != expected_hash:
            return {
                "valid": False,
                "count": count + 1,
                "log_id": log_id,
                "reason": "action_hash does not match action fields, created_at, and previous_hash",
            }
        expected_previous = row["action_hash"]
        count += 1

    return {"valid": True, "count": count}


def verify_chain_integrity(table: str, engine) -> bool:
    """Verify record_hashes or fully recompute action hashes in audit_log.

    ``engine`` must be a SQLAlchemy engine connected to the target database.
    No module-level engine is used; callers must pass one explicitly.
    """

    if table == "record_hashes":

        with engine.connect() as conn:

            rows = conn.execute(text("""
                SELECT
                    rh.hash_id,
                    rh.record_hash,
                    rh.previous_hash,
                    ce.cin,
                    ce.company_name_normalized,
                    ce.address_normalized,
                    ce.authorized_capital,
                    ce.company_status
                FROM record_hashes rh
                JOIN cleaned_entities ce
                    ON rh.entity_id = ce.entity_id
                ORDER BY rh.hash_id
            """)).mappings().all()

        expected_previous = ""

        for i, row in enumerate(rows):

            # Check that the stored previous hash points
            # to the previous record in the chain.
            if row["previous_hash"] != expected_previous:

                print(
                    f"BROKEN CHAIN at row {i}: "
                    f"previous_hash link is invalid"
                )

                return False

            # Recompute the hash from the actual entity data.
            expected_hash = compute_record_hash(
                row,
                expected_previous
            )

            # Detect modification of the stored record_hash.
            if row["record_hash"] != expected_hash:

                print(
                    f"BROKEN CHAIN at row {i}: "
                    f"record_hash does not match the expected hash"
                )

                return False

            expected_previous = row["record_hash"]

        print(
            f"SUCCESS: {table} chain verified intact "
            f"across {len(rows)} rows"
        )

        return True

    elif table == "audit_log":
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT log_id, action_type, cluster_id, reviewer, created_at,
                       action_hash, previous_hash
                FROM audit_log
                ORDER BY log_id
            """)).mappings().all()

        result = verify_audit_chain_rows(rows)
        if not result["valid"]:
            print(f"BROKEN CHAIN at log_id {result['log_id']}: {result['reason']}")
            return False
        print(f"SUCCESS: audit_log chain verified intact across {result['count']} rows")
        return True

    else:

        raise ValueError(
            "table must be 'record_hashes' or 'audit_log'"
        )
