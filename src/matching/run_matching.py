import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Dynamically add src/blocking to sys.path relative to this file's location
blocking_path = Path(__file__).resolve().parent.parent / "blocking"
sys.path.append(str(blocking_path))

from blocker import generate_candidate_pairs
from scorer import score_candidate_pairs

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise ValueError("DATABASE_URL not found in .env file.")

# pool_pre_ping=True automatically reconnects if the connection dropped while scoring
engine = create_engine(db_url, pool_pre_ping=True)


def run():
    print("Pulling cleaned_entities from Neon...")
    entities = pd.read_sql(
        "SELECT entity_id, pincode, company_name_normalized, address_normalized FROM cleaned_entities",
        engine,
    )
    print(f"Loaded {len(entities):,} entities.")

    print("Generating candidate pairs locally in memory...")
    pairs = generate_candidate_pairs(entities)
    pairs["pair_id"] = range(1, len(pairs) + 1)
    print(f"Generated {len(pairs):,} candidate pairs locally.")

    print("Scoring candidate pairs locally using Jaro-Winkler...")
    scored = score_candidate_pairs(pairs, entities)

    # Filter strictly for matches to minimize storage footprint
    matches_only = scored[scored["is_match"] == True]
    match_rate = (
        (len(matches_only) / len(scored)) * 100 if len(scored) > 0 else 0.0
    )
    print(
        f"Identified {len(matches_only):,} matches out of {len(scored):,} pairs ({match_rate:.2f}%)."
    )

    # Re-create scored_pairs directly with INTEGER entity IDs
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS scored_pairs CASCADE;"))
        conn.execute(
            text("""
            CREATE TABLE scored_pairs (
                pair_id INTEGER PRIMARY KEY,
                entity_id_a INTEGER,
                entity_id_b INTEGER,
                address_similarity FLOAT,
                name_similarity FLOAT,
                is_match BOOLEAN,
                scored_at TIMESTAMP DEFAULT NOW()
            );
        """)
        )

    print("Preparing payload for Neon database upload...")
    upload = matches_only.merge(
        pairs[["pair_id", "entity_id_a", "entity_id_b"]], on="pair_id"
    )

    upload["entity_id_a"] = upload["entity_id_a"].astype(int)
    upload["entity_id_b"] = upload["entity_id_b"].astype(int)

    upload = upload[
        [
            "pair_id",
            "entity_id_a",
            "entity_id_b",
            "address_similarity",
            "name_similarity",
            "is_match",
        ]
    ]

    print("Uploading matched pairs to Neon...")
    upload.to_sql(
        "scored_pairs",
        engine,
        if_exists="append",
        index=False,
        chunksize=10000,
    )

    print(
        f"SUCCESS: Pushed {len(upload):,} matched pairs to Neon table 'scored_pairs'."
    )


if __name__ == "__main__":
    run()