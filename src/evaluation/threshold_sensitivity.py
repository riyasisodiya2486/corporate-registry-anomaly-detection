import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

sys.path.append(str(Path(__file__).resolve().parent.parent / "blocking"))
sys.path.append(str(Path(__file__).resolve().parent.parent / "matching"))
from blocker import generate_candidate_pairs
import jellyfish

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

def score_at_thresholds(pairs, entities, addr_thresholds, name_thresholds):
    fields = entities.set_index("entity_id")[["company_name_normalized", "address_normalized"]]
    merged = pairs.merge(fields, left_on="entity_id_a", right_index=True).merge(
        fields, left_on="entity_id_b", right_index=True, suffixes=("_a", "_b"))
    merged["name_sim"] = [jellyfish.jaro_winkler_similarity(a or "", b or "") for a, b in
                           zip(merged["company_name_normalized_a"], merged["company_name_normalized_b"])]
    merged["addr_sim"] = [jellyfish.jaro_winkler_similarity(a or "", b or "") for a, b in
                           zip(merged["address_normalized_a"], merged["address_normalized_b"])]

    results = []
    for at in addr_thresholds:
        for nt in name_thresholds:
            match_count = ((merged["addr_sim"] >= at) | (merged["name_sim"] >= nt)).sum()
            results.append({"address_threshold": at, "name_threshold": nt,
                            "match_count": int(match_count), "match_rate": round(match_count / len(merged), 4)})
    return pd.DataFrame(results)

def run():
    entities = pd.read_sql("SELECT entity_id, pincode, company_name_normalized, address_normalized FROM cleaned_entities", engine)
    sample = entities.sample(n=min(20000, len(entities)), random_state=42)
    pairs = generate_candidate_pairs(sample)
    pairs = pairs.reset_index(drop=True)

    result = score_at_thresholds(pairs, sample,
                                   addr_thresholds=[0.80, 0.85, 0.90, 0.95],
                                   name_thresholds=[0.85, 0.90, 0.95, 0.98])
    result.to_csv("results/threshold_sensitivity.csv", index=False)
    print(result.to_string(index=False))
    print(f"\nSUCCESS: saved to results/threshold_sensitivity.csv — real data for your Evaluation section")

if __name__ == "__main__":
    run()