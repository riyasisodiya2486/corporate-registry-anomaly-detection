"""Chain pending reviewer rows through the existing integrity audit log.

This script requires V2_DATABASE_URL so it cannot silently target DATABASE_URL.
The app role does not write to audit_log; run this owner-side after review sessions.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from src.integrity.hash_chain import acquire_audit_chain_lock, log_audit_action

def chain_pending_reviews(engine, audit_action=None):
    """Audit each unchained review using hash_chain.log_audit_action's API."""
    if audit_action is None:
        audit_action = log_audit_action

    with engine.begin() as conn:
        # Lock before selecting pending rows so a competing run waits, then sees
        # the committed chain_hash values instead of processing stale rows.
        acquire_audit_chain_lock(conn)
        rows = conn.execute(
            text(
                "SELECT review_id, cluster_id, reviewer, review_mode, verdict "
                "FROM reviewer_reviews WHERE chain_hash IS NULL "
                "ORDER BY review_id FOR UPDATE"
            )
        ).fetchall()
        for row in rows:
            chain_hash = audit_action(
                f"review:{row.review_mode}:{row.verdict}",
                int(row.cluster_id),
                row.reviewer,
                connection=conn,
            )
            result = conn.execute(
                text("UPDATE reviewer_reviews SET chain_hash = :h WHERE review_id = :i"),
                {"h": chain_hash, "i": int(row.review_id)},
            )
            if result.rowcount != 1:
                raise RuntimeError(f"Expected to update review_id {row.review_id} exactly once")
    return len(rows)


def main():
    load_dotenv()
    database_url = os.environ.get("V2_DATABASE_URL")
    if not database_url:
        raise SystemExit("Set V2_DATABASE_URL to the isolated V2 database before running.")
    configured_database_url = os.environ.get("DATABASE_URL")
    if configured_database_url and make_url(configured_database_url) == make_url(database_url):
        raise SystemExit("V2_DATABASE_URL must be distinct from DATABASE_URL; refusing to run.")

    engine = create_engine(database_url)
    try:
        count = chain_pending_reviews(engine, audit_action=log_audit_action)
        print(f"{count} reviews chained")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
