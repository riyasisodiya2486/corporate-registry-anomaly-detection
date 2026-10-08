import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import IsolationForest
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

# status_signal_score is DELIBERATELY excluded. It exists only for the separate weak-signal
# correlation check (Experiment 5). Feeding it to the model and then correlating the model's
# output with status would be circular -- exactly the flaw this project was designed to avoid.
FEATURE_COLS = [
    "address_signal_score", "name_signal_score", "timing_signal_score",
    "capital_similarity_score", "topology_score", "category_homogeneity_score", "bridge_flag",
]
HIGH_PRIORITY_PERCENTILE = 95
MODERATE_PERCENTILE = 80


def run():
    print("Loading cluster_scores from Neon...")
    df = pd.read_sql("SELECT * FROM cluster_scores", engine)
    print(f"{len(df):,} clusters loaded.")

    X = df[FEATURE_COLS].copy()
    X["bridge_flag"] = X["bridge_flag"].astype(int)

    print("Training Isolation Forest...")
    model = IsolationForest(n_estimators=200, contamination="auto", random_state=42)
    model.fit(X)

    # sklearn convention: score_samples is LOWER for more abnormal points. Negate so that,
    # in our own scores, higher always means more anomalous -- matches every score elsewhere
    # in this project (address_signal_score, name_signal_score, etc. are all "higher = more unusual").
    raw = -model.score_samples(X)
    composite = 100 * (raw - raw.min()) / (raw.max() - raw.min())
    composite = np.clip(composite, 0, 100)

    p_high, p_mod = np.percentile(composite, [HIGH_PRIORITY_PERCENTILE, MODERATE_PERCENTILE])
    flag = np.select([composite >= p_high, composite >= p_mod], ["high_priority", "moderate"], default="baseline")

    df["isolation_forest_score"] = raw
    df["composite_score"] = composite.round(2)
    df["flag_category"] = flag

    print(f"Writing {len(df):,} rows back via staged bulk update...")
    update_df = df[[
        "cluster_id",
        "isolation_forest_score",
        "composite_score",
        "flag_category",
    ]]

    with engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TEMP TABLE cluster_scores_staging (
                    cluster_id INTEGER,
                    isolation_forest_score FLOAT,
                    composite_score FLOAT,
                    flag_category TEXT
                ) ON COMMIT DROP;
            """)
        )

        update_df.to_sql(
            "cluster_scores_staging",
            conn,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

        conn.execute(
            text("""
                UPDATE cluster_scores cs
                SET isolation_forest_score = s.isolation_forest_score,
                    composite_score = s.composite_score,
                    flag_category = s.flag_category
                FROM cluster_scores_staging s
                WHERE cs.cluster_id = s.cluster_id;
            """)
        )

    print("SUCCESS: bulk update complete")

    print(f"\nSUCCESS: scored {len(df):,} clusters")
    print(f"Thresholds -- high_priority >= {p_high:.2f} | moderate >= {p_mod:.2f}")
    print(df["flag_category"].value_counts())
    print("\nTop 10 highest composite_score clusters:")
    print(df.sort_values("composite_score", ascending=False)
            .head(10)[["cluster_id", "cluster_size", "composite_score", "flag_category"] + FEATURE_COLS]
            .to_string(index=False))

    # Weak-signal correlation check (Experiment 5) -- status_signal_score was never seen by the
    # model, so this comparison is not circular.
    high = df[df["flag_category"] == "high_priority"]["status_signal_score"].mean()
    overall = df["status_signal_score"].mean()
    print(f"\nWeak-signal check: mean status_signal_score in high_priority clusters = {high:.2f}"
          f" vs. overall mean = {overall:.2f} (directional only, NOT validation)")


if __name__ == "__main__":
    run()