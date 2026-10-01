import os

import numpy as np
import pandas as pd
import shap
from dotenv import load_dotenv
from sklearn.ensemble import IsolationForest
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

FEATURE_COLS = [
    "address_signal_score", "name_signal_score", "timing_signal_score",
    "capital_similarity_score", "topology_score", "category_homogeneity_score", "bridge_flag",
]
TOP_N_SHAP_FEATURES = 3


def run():
    print("Loading cluster_scores from Neon...")
    df = pd.read_sql("SELECT * FROM cluster_scores", engine)
    X = df[FEATURE_COLS].copy()
    X["bridge_flag"] = X["bridge_flag"].astype(int)

    # Re-fit with the SAME random_state as run_isolation_forest.py so this model is identical
    # to the one that actually produced composite_score -- explanations must match what was scored.
    model = IsolationForest(n_estimators=200, contamination="auto", random_state=42)
    model.fit(X)

    # Extract raw anomaly scores (-score_samples) matching composite_score logic
    raw = -model.score_samples(X)

    print("Computing SHAP values (TreeExplainer supports IsolationForest directly)...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    # --- Verify SHAP's sign convention against our own composite_score convention ---
    reconstructed = shap_values.sum(axis=1) + explainer.expected_value
    correlation = np.corrcoef(reconstructed, raw)[0, 1]

    print(f"\nSHAP sign check: correlation = {correlation:.3f}")
    if correlation < 0:
        print("CONFIRMED: SHAP is in the OPPOSITE orientation to our convention. Negating shap_values below.")
        shap_values = -shap_values
    else:
        print("CONFIRMED: SHAP already matches our convention (higher = more anomalous). No change needed.\n")

    print("Writing cluster_explanations...")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cluster_explanations;"))
        conn.execute(text("""
            CREATE TABLE cluster_explanations (
                explanation_id SERIAL PRIMARY KEY,
                cluster_id INTEGER REFERENCES cluster_scores(cluster_id),
                feature_name TEXT,
                shap_value FLOAT,
                rank INTEGER,
                computed_at TIMESTAMP DEFAULT NOW()
            );
        """))

    rows = []
    for i, cluster_id in enumerate(df["cluster_id"]):
        contributions = list(zip(FEATURE_COLS, shap_values[i]))
        contributions.sort(key=lambda x: abs(x[1]), reverse=True)
        for rank, (feature_name, value) in enumerate(contributions[:TOP_N_SHAP_FEATURES], start=1):
            rows.append({"cluster_id": int(cluster_id), "feature_name": feature_name,
                         "shap_value": float(value), "rank": rank})

    pd.DataFrame(rows).to_sql("cluster_explanations", engine, if_exists="append", index=False)
    print(f"SUCCESS: wrote {len(rows):,} explanation rows for {len(df):,} clusters")

    top_cluster = df.sort_values("composite_score", ascending=False).iloc[0]["cluster_id"]
    print(f"\nExample -- top explanations for cluster {int(top_cluster)}:")
    example = [r for r in rows if r["cluster_id"] == int(top_cluster)]
    for r in example:
        print(f"  rank {r['rank']}: {r['feature_name']} (SHAP={r['shap_value']:.3f})")


if __name__ == "__main__":
    run()