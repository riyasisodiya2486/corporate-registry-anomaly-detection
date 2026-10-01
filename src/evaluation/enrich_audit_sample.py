import os
import csv
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

def run():
    results_dir = Path(__file__).resolve().parent.parent.parent / "results"
    input_path = results_dir / "audit_sample.csv"
    output_path = results_dir / "audit_sample_enriched.csv"

    if not input_path.exists():
        input_path = Path("results/audit_sample.csv")

    # Use python engine to cleanly parse quoted notes
    audit = pd.read_csv(input_path, engine="python")

    # Clean up extra columns if accidental trailing commas were present
    expected_cols = ["cluster_id", "cluster_size", "composite_score", "flag_category", "audit_group", "human_verdict", "notes"]
    audit = audit.iloc[:, :len(expected_cols)]
    audit.columns = expected_cols

    explanations = pd.read_sql("""
        SELECT cluster_id, feature_name, shap_value, rank
        FROM cluster_explanations 
        WHERE rank <= 3 
        ORDER BY cluster_id, rank
    """, engine)

    def top_reasons(cluster_id):
        rows = explanations[explanations["cluster_id"] == cluster_id]
        if rows.empty:
            return ""
        return "; ".join(f"{r.feature_name} ({r.shap_value:.2f})" for r in rows.itertuples())

    audit["shap_top_reasons"] = audit["cluster_id"].apply(top_reasons)
    
    if "shap_agrees_with_human" not in audit.columns:
        audit["shap_agrees_with_human"] = ""

    # Quote non-numeric fields so future commas inside text won't break parsing
    audit.to_csv(output_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"SUCCESS: wrote {len(audit)} rows with SHAP reasons attached to {output_path}")

if __name__ == "__main__":
    run()
