import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from hash_chain import log_audit_action, NEON_ENGINE


load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])


def log_high_priority_clusters():
    print("Loading high-priority clusters from Neon...")

    df = pd.read_sql(
        """
        SELECT cluster_id
        FROM cluster_scores
        WHERE flag_category = 'high_priority'
        ORDER BY cluster_id
        """,
        engine,
    )

    print(f"{len(df):,} high-priority clusters found.")

    for cluster_id in df["cluster_id"]:
        log_audit_action(
            "flagged",
            int(cluster_id),
            "system",
            db_engine=NEON_ENGINE,
        )

    print(f"SUCCESS: logged {len(df):,} flagged clusters.")


if __name__ == "__main__":
    log_high_priority_clusters()