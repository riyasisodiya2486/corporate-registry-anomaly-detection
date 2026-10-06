import hashlib
import os

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

LOCAL_ENGINE = create_engine(
    "postgresql://admin:admin123@localhost:5432/registry"
)
engine = LOCAL_ENGINE

NEON_ENGINE = create_engine(os.environ["DATABASE_URL"])


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


def hash_all_entities():
    """Build the hash chain over all cleaned entities using batched inserts."""

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


def log_audit_action(action_type: str, cluster_id, reviewer: str, db_engine=None) -> str:
    """Write one audit_log row, chaining it from the previous audit action."""

    if db_engine is None:
        db_engine = LOCAL_ENGINE

    with db_engine.connect() as conn:

        last = conn.execute(
            text(
                "SELECT action_hash "
                "FROM audit_log "
                "ORDER BY log_id DESC LIMIT 1"
            )
        ).fetchone()

        previous_hash = last[0] if last else ""

        import datetime

        timestamp = datetime.datetime.now().isoformat()

        payload = (
            f"{action_type}|{cluster_id}|{reviewer}|"
            f"{timestamp}|{previous_hash}"
        )

        action_hash = hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()

        conn.execute(
            text("""
                INSERT INTO audit_log
                    (action_type, cluster_id, reviewer,
                     action_hash, previous_hash)
                VALUES
                    (:at, :cid, :rev, :ah, :ph)
            """),
            {
                "at": action_type,
                "cid": cluster_id,
                "rev": reviewer,
                "ah": action_hash,
                "ph": previous_hash
            }
        )

        conn.commit()

        return action_hash


def verify_chain_integrity(table: str) -> bool:
    """Verify hash-chain links and recompute record hashes when checking record_hashes."""

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

        hash_col = "action_hash"
        id_col = "log_id"

    else:

        raise ValueError(
            "table must be 'record_hashes' or 'audit_log'"
        )

    with engine.connect() as conn:

        rows = conn.execute(
            text(f"""
                SELECT {hash_col}, previous_hash
                FROM {table}
                ORDER BY {id_col}
            """)
        ).all()

    expected_previous = ""

    for i, (current_hash, stored_previous) in enumerate(rows):

        if stored_previous != expected_previous:

            print(
                f"BROKEN CHAIN at row {i}: "
                f"previous_hash link is invalid"
            )

            return False

        expected_previous = current_hash

    print(
        f"SUCCESS: {table} chain verified intact "
        f"across {len(rows)} rows"
    )

    return True