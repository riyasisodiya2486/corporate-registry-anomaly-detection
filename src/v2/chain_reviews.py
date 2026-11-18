"""Yashika (owner connection). Chains each new review into the hash-chain audit_log, then stores the hash.
The app role can only INSERT reviews; it never writes to audit_log. Run this after each review session.
TODO Yashika: fix the import path to your real integrity module."""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.integrity.audit_log import log_audit_action    # TODO: real module path (log_audit_action(conn, action_type, cluster_id, reviewer) -> hash)

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

with engine.begin() as conn:
    rows = conn.execute(text(
        "SELECT review_id, cluster_id, reviewer, review_mode, verdict FROM reviewer_reviews "
        "WHERE chain_hash IS NULL ORDER BY review_id")).fetchall()
    for r in rows:
        h = log_audit_action(conn, f"review:{r.review_mode}:{r.verdict}", int(r.cluster_id), r.reviewer)
        conn.execute(text("UPDATE reviewer_reviews SET chain_hash = :h WHERE review_id = :i"),
                     {"h": h, "i": int(r.review_id)})
print(len(rows), "reviews chained")
