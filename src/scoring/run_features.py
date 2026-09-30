import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parent.parent / "blocking"))
sys.path.append(str(Path(__file__).resolve().parent.parent / "matching"))
from blocker import generate_candidate_pairs          # noqa: E402
from scorer import score_candidate_pairs              # noqa: E402
from features import compute_cluster_features, find_bridge_clusters   # noqa: E402

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])


def run():
    print("Loading tables from Neon...")
    entities = pd.read_sql(
        """SELECT entity_id, pincode, company_name_normalized, address_normalized, nic_code,
                  date_of_registration, authorized_capital, company_status
           FROM cleaned_entities""", engine)
    assignments = pd.read_sql("SELECT entity_id, cluster_id FROM cluster_assignments", engine)
    edges = pd.read_sql("SELECT entity_id_a, entity_id_b, name_similarity, address_similarity FROM scored_pairs WHERE is_match = TRUE", engine)
    edges["entity_id_a"] = pd.to_numeric(edges["entity_id_a"]).astype(int)
    edges["entity_id_b"] = pd.to_numeric(edges["entity_id_b"]).astype(int)
    print(f"{len(entities):,} entities | {assignments['cluster_id'].nunique():,} clusters | {len(edges):,} matched edges")

    print("Bridge detection: regenerating + rescoring candidate pairs locally (a few minutes, nothing is stored)...")
    bridge_clusters = find_bridge_clusters(entities, assignments, generate_candidate_pairs, score_candidate_pairs)

    print("Computing the 7 structural signals for every cluster...")
    feats = compute_cluster_features(entities, assignments, edges, bridge_clusters)

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cluster_scores CASCADE;"))
        conn.execute(text("""
            CREATE TABLE cluster_scores (
                cluster_id INTEGER PRIMARY KEY,
                cluster_size INTEGER,
                address_signal_score FLOAT,
                name_signal_score FLOAT,
                timing_signal_score FLOAT,
                status_signal_score FLOAT,
                capital_similarity_score FLOAT,
                topology_score FLOAT,
                bridge_flag BOOLEAN,
                category_homogeneity_score FLOAT,
                isolation_forest_score FLOAT,
                composite_score FLOAT,
                flag_category TEXT,
                scored_at TIMESTAMP DEFAULT NOW()
            );
        """))
    feats.to_sql("cluster_scores", engine, if_exists="append", index=False)

    print(f"\nSUCCESS: wrote {len(feats):,} cluster feature rows")
    print(f"Clusters flagged as bridges: {int(feats['bridge_flag'].sum()):,} ({feats['bridge_flag'].mean():.1%})")
    print("\nSignal summary (mean / max):")
    cols = [c for c in feats.columns if c.endswith("_score")]
    print(feats[cols].agg(["mean", "max"]).round(2).T)
    print("\nTop 5 by address_signal_score:")
    print(feats.sort_values("address_signal_score", ascending=False).head(5).to_string(index=False))


if __name__ == "__main__":
    run()