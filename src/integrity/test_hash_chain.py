"""Destructive database test for hash-chain verification.

NEVER EXECUTE against production or Neon. This test truncates and mutates
database tables (record_hashes, audit_log). It is intentionally opt-in:

    ALLOW_DESTRUCTIVE_TESTS=1 python src/integrity/test_hash_chain.py

and requires DATABASE_URL to point at an isolated test database only.
"""
import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from hash_chain import (
    hash_all_entities,
    log_audit_action,
    verify_chain_integrity,
)


PROHIBITED_HOSTS = {"neon.tech", "neon-prod", "prod"}


def _is_isolated_local_db(database_url: str) -> bool:
    """Return True only if the URL targets an isolated local test database."""
    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal"):
        return True
    if any(prohibited in host for prohibited in PROHIBITED_HOSTS):
        return False
    return False


def main() -> int:
    load_dotenv()
    if os.environ.get("ALLOW_DESTRUCTIVE_TESTS") != "1":
        print(
            "Refusing to run destructive test: set ALLOW_DESTRUCTIVE_TESTS=1 "
            "and DATABASE_URL to an isolated test database to enable."
        )
        return 0

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL must be set to an isolated test database.")
        return 1

    if not _is_isolated_local_db(database_url):
        print("Refusing to run destructive test against non-local or cloud database.")
        return 1

    engine = create_engine(database_url)
    try:
        # Step 1: Build the hash chain over the cleaned data
        hash_all_entities(engine)

        # Step 2: Verify the untampered chain
        print("\n--- Verifying untampered chain ---")
        verify_chain_integrity("record_hashes", engine)

        # Step 3: Reset audit log for a clean demonstration
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE audit_log RESTART IDENTITY"))
            conn.commit()

        # Step 4: Log two audit actions
        log_audit_action(
            "flagged",
            cluster_id=1,
            reviewer="system",
            db_engine=engine,
        )

        log_audit_action(
            "reviewed_confirmed",
            cluster_id=1,
            reviewer="Yashika",
            db_engine=engine,
        )

        print("\n--- Verifying audit_log chain ---")
        verify_chain_integrity("audit_log", engine)

        # Step 5: Deliberately tamper with row 5
        print("\n--- Deliberately tampering with row 5 ---")

        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE record_hashes
                    SET record_hash = 'TAMPERED'
                    WHERE hash_id = 5
                """)
            )
            conn.commit()

        # Step 6: Verify again
        print("--- Re-verifying after tampering ---")
        verify_chain_integrity("record_hashes", engine)
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())