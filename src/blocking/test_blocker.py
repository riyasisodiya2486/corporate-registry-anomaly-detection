import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from src.blocking.blocker import generate_candidate_pairs


CHUNK_SIZE = 50_000


def run():
    load_dotenv()

    engine = create_engine(os.getenv("DATABASE_URL"))

    print("Loading cleaned entities...")

    entities = pd.read_sql(
        """
        SELECT entity_id, pincode, company_name_normalized
        FROM cleaned_entities
        """,
        engine,
    )

    total_entities = len(entities)
    naive_comparisons = total_entities * (total_entities - 1) // 2

    print(f"Total entities: {total_entities:,}")
    print(f"Naive all-pairs comparisons: {naive_comparisons:,}")

    print("\nGenerating candidate pairs...")

    pairs = generate_candidate_pairs(entities)

    candidate_count = len(pairs)
    reduction_ratio = 1 - (candidate_count / naive_comparisons)

    print(f"Candidate pairs after blocking: {candidate_count:,}")
    print(f"Reduction ratio: {reduction_ratio:.4%}")

    print("\nInserting candidate pairs in batches...")

    for start in range(0, candidate_count, CHUNK_SIZE):
        chunk = pairs.iloc[start:start + CHUNK_SIZE]

        chunk.to_sql(
            "candidate_pairs",
            engine,
            if_exists="append",
            index=False,
            method="multi",
        )

        end = min(start + CHUNK_SIZE, candidate_count)

        print(
            f"Inserted {end:,}/{candidate_count:,} "
            f"candidate pairs"
        )

    print(
        f"\nSUCCESS: wrote {candidate_count:,} "
        "candidate pairs to database"
    )


if __name__ == "__main__":
    run()