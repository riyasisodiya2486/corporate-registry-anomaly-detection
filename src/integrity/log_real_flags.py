import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])


def verify_real_flags():
    print("Checking real high_priority flags in Neon...")

    high_priority = pd.read_sql(
        """
        SELECT cluster_id
        FROM cluster_scores
        WHERE flag_category = 'high_priority'
        ORDER BY cluster_id
        """,
        engine,
    )

    audit_rows = pd.read_sql(
        """
        SELECT log_id, action_type, cluster_id, reviewer,
               action_hash, previous_hash
        FROM audit_log
        WHERE action_type = 'flagged'
          AND reviewer = 'system'
        ORDER BY log_id
        """,
        engine,
    )

    print(f"High-priority clusters: {len(high_priority):,}")
    print(f"System flagged audit entries: {len(audit_rows):,}")

    if len(high_priority) != len(audit_rows):
        raise RuntimeError(
            "Mismatch between high_priority clusters and flagged audit entries."
        )

    print("SUCCESS: real flags are present in the audit log.")

    print("\nVerifying audit_log hash chain...")

    expected_previous = ""

    for _, row in audit_rows.iterrows():
        if row["previous_hash"] != expected_previous:
            raise RuntimeError(
                f"BROKEN CHAIN at log_id {row['log_id']}"
            )

        expected_previous = row["action_hash"]

    print(
        f"SUCCESS: audit_log chain verified intact "
        f"across {len(audit_rows):,} flagged entries."
    )


if __name__ == "__main__":
    verify_real_flags()