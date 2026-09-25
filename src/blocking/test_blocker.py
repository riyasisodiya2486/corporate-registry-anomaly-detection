import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"))


def run():
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO candidate_pairs (
                entity_id_a,
                entity_id_b,
                blocking_method
            )
            SELECT
                a.entity_id,
                b.entity_id,
                'pincode'
            FROM cleaned_entities a
            JOIN cleaned_entities b
                ON a.pincode = b.pincode
                AND a.entity_id < b.entity_id
            WHERE a.pincode IS NOT NULL
        """))

        conn.execute(text("""
            INSERT INTO candidate_pairs (
                entity_id_a,
                entity_id_b,
                blocking_method
            )
            SELECT
                a.entity_id,
                b.entity_id,
                'name_prefix'
            FROM cleaned_entities a
            JOIN cleaned_entities b
                ON LEFT(a.company_name_normalized, 4)
                 = LEFT(b.company_name_normalized, 4)
                AND a.entity_id < b.entity_id
            WHERE a.company_name_normalized IS NOT NULL
              AND LENGTH(a.company_name_normalized) >= 4
              AND b.company_name_normalized IS NOT NULL
              AND LENGTH(b.company_name_normalized) >= 4
        """))

        conn.execute(text("""
            DELETE FROM candidate_pairs cp
            USING candidate_pairs duplicate
            WHERE cp.pair_id > duplicate.pair_id
              AND cp.entity_id_a = duplicate.entity_id_a
              AND cp.entity_id_b = duplicate.entity_id_b
        """))

        total_entities = conn.execute(
            text("SELECT COUNT(*) FROM cleaned_entities")
        ).scalar()

        candidate_count = conn.execute(
            text("SELECT COUNT(*) FROM candidate_pairs")
        ).scalar()

    naive_comparisons = (
        total_entities * (total_entities - 1) // 2
    )

    reduction_ratio = 1 - (
        candidate_count / naive_comparisons
    )

    print(f"Total entities: {total_entities}")
    print(
        f"Naive all-pairs comparisons: "
        f"{naive_comparisons:,}"
    )
    print(
        f"Candidate pairs after blocking: "
        f"{candidate_count:,}"
    )
    print(
        f"Reduction ratio: "
        f"{reduction_ratio:.4%}"
    )
    print(
        f"SUCCESS: wrote "
        f"{candidate_count} candidate pairs to database"
    )


if __name__ == "__main__":
    run()