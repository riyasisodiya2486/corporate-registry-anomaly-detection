import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

def run():
    # Ensure output directory exists as an absolute path
    output_dir = Path(__file__).resolve().parent.parent.parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "audit_sample.csv"

    # Top 20 flagged clusters
    top_flagged = pd.read_sql("""
        SELECT cluster_id, cluster_size, composite_score, flag_category
        FROM cluster_scores ORDER BY composite_score DESC LIMIT 20
    """, engine)

    # Random sample of 20 baseline clusters
    baseline_sample = pd.read_sql("""
        SELECT cluster_id, cluster_size, composite_score, flag_category
        FROM cluster_scores WHERE flag_category = 'baseline'
        ORDER BY RANDOM() LIMIT 20
    """, engine)

    combined = pd.concat([
        top_flagged.assign(audit_group="top_flagged"),
        baseline_sample.assign(audit_group="baseline_sample")
    ])
    
    combined["human_verdict"] = ""
    combined["notes"] = ""

    combined.to_csv(output_path, index=False)
    print(f"SUCCESS: wrote {len(combined)} rows to {output_path} for manual review")

if __name__ == "__main__":
    run()