import pandas as pd
from sqlalchemy import create_engine
from scorer import score_candidate_pairs

engine = create_engine("postgresql://admin:admin123@localhost:5432/registry")

def run():
    # Fetch candidate pairs created by Yashika's blocking layer with primary key pair_id
    pairs = pd.read_sql("SELECT pair_id, entity_id_a, entity_id_b FROM candidate_pairs", engine)
    entities = pd.read_sql("SELECT entity_id, company_name_normalized, address_normalized FROM cleaned_entities", engine)

    print(f"Scoring {len(pairs)} real candidate pairs...")
    scored = score_candidate_pairs(pairs, entities)

    # Write score results to the database
    scored.to_sql("scored_pairs", engine, if_exists="append", index=False)

    match_count = scored["is_match"].sum()
    match_pct = (match_count / len(scored)) * 100 if len(scored) > 0 else 0
    print(f"SUCCESS: {match_count} of {len(scored)} pairs scored as matches ({match_pct:.1f}%)")

if __name__ == "__main__":
    run()