"""Benchmark the existing blocker and scorer on an isolated V2 CSV only.

The benchmark reads results/v2/cleaned_entities.csv by default. It never loads the
V1 results/snapshot data or connects to a database.
"""
import math
import sys
import time
from pathlib import Path

import pandas as pd

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT / "blocking"))
sys.path.insert(0, str(SOURCE_ROOT / "matching"))

from blocker import MAX_BLOCK_SIZE, generate_candidate_pairs  # noqa: E402
from scorer import score_candidate_pairs  # noqa: E402

V2_ENTITIES = Path("results/v2/cleaned_entities.csv")
OUT = Path("results/v2")
FRACTIONS = (0.25, 0.50, 0.75, 1.00)
REQUIRED_COLUMNS = {
    "entity_id",
    "pincode",
    "company_name_normalized",
    "address_normalized",
}


def run_blocking(entities_df):
    """Generate V1-compatible candidate pairs and add the scorer's pair_id."""
    _validate_entities(entities_df, {"entity_id", "pincode", "company_name_normalized"})

    # The V1 combined blocker raises KeyError when both block generators return
    # empty, columnless frames. Detect that valid case without changing V1 code.
    if not _has_candidate_pair(entities_df):
        return pd.DataFrame(columns=["pair_id", "entity_id_a", "entity_id_b"])

    pairs = generate_candidate_pairs(entities_df)
    if not {"entity_id_a", "entity_id_b"}.issubset(pairs.columns):
        if not pairs.empty:
            raise ValueError("Candidate generator returned an unexpected pair schema")
        pairs = pd.DataFrame(columns=["entity_id_a", "entity_id_b"])
    pairs = pairs.reset_index(drop=True).copy()
    if "pair_id" in pairs:
        raise ValueError("Candidate generator unexpectedly returned pair_id")
    pairs.insert(0, "pair_id", range(1, len(pairs) + 1))
    return pairs


def run_scoring(pairs, entities_df):
    """Score candidate pairs using score_candidate_pairs(pairs, entities)."""
    _validate_entities(entities_df, REQUIRED_COLUMNS)
    if not {"pair_id", "entity_id_a", "entity_id_b"}.issubset(pairs.columns):
        raise ValueError("Pairs must contain pair_id, entity_id_a, and entity_id_b")
    if pairs.empty:
        return pd.DataFrame(
            columns=["pair_id", "address_similarity", "name_similarity", "is_match"]
        )
    return score_candidate_pairs(pairs, entities_df)


def _validate_entities(entities_df, required_columns):
    missing = set(required_columns) - set(entities_df.columns)
    if missing:
        raise ValueError(f"V2 entity input is missing columns: {sorted(missing)}")
    if entities_df["entity_id"].isna().any():
        raise ValueError("entity_id values must not be null")
    if entities_df["entity_id"].duplicated().any():
        raise ValueError("entity_id values must be unique before blocking or scoring")


def _has_candidate_pair(entities_df):
    """Mirror the V1 block size rules only to handle its empty-result edge case."""
    for _, group in entities_df.dropna(subset=["pincode"]).groupby("pincode"):
        if 1 < len(group) <= MAX_BLOCK_SIZE:
            return True
        if len(group) > MAX_BLOCK_SIZE:
            sub = group.assign(
                subkey=group["company_name_normalized"].fillna("").str[:6]
            )
            if any(1 < len(subgroup) <= MAX_BLOCK_SIZE for _, subgroup in sub.groupby("subkey")):
                return True

    valid = entities_df.dropna(subset=["company_name_normalized"])
    prefixed = valid.assign(prefix=valid["company_name_normalized"].str[:6])
    return any(
        len(prefix) >= 6 and 1 < len(group) <= MAX_BLOCK_SIZE
        for prefix, group in prefixed.groupby("prefix")
    )


def run_benchmark(entities, fractions=FRACTIONS):
    """Run nested fractions from one deterministic shuffle of the same dataset."""
    _validate_entities(entities, REQUIRED_COLUMNS)
    if entities.empty:
        raise ValueError("V2 entity input is empty")
    if not fractions or any(not 0 < fraction <= 1 for fraction in fractions):
        raise ValueError("fractions must be a non-empty sequence in (0, 1]")
    if list(fractions) != sorted(set(fractions)):
        raise ValueError("fractions must be unique and increasing so subsets remain nested")

    ordered = entities.sort_values("entity_id", kind="stable").reset_index(drop=True)
    shuffled = ordered.sample(frac=1, random_state=7).reset_index(drop=True)
    rows = []
    for fraction in fractions:
        count = len(shuffled) if fraction == 1 else max(1, math.ceil(len(shuffled) * fraction))
        subset = shuffled.iloc[:count].copy()

        start = time.perf_counter()
        pairs = run_blocking(subset)
        blocked = time.perf_counter()
        run_scoring(pairs, subset)
        scored = time.perf_counter()
        blocking_s = round(blocked - start, 4)
        scoring_s = round(scored - blocked, 4)
        row = {
            "fraction": fraction,
            "records": len(subset),
            "pairs": len(pairs),
            "blocking_s": blocking_s,
            "scoring_s": scoring_s,
            "total_s": round(blocking_s + scoring_s, 4),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def save_scaling_plot(results, output_path):
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots()
    try:
        axis.plot(results.records, results.total_s, marker="o")
        axis.set_xlabel("Records")
        axis.set_ylabel("Seconds (blocking + scoring)")
        axis.set_title("Runtime against V2 input size")
        figure.tight_layout()
        figure.savefig(output_path, dpi=200)
    finally:
        plt.close(figure)


def main():
    if not V2_ENTITIES.is_file():
        raise SystemExit(
            f"V2 input not found: {V2_ENTITIES}. Provide an approved isolated V2 dataset; "
            "the V1 results/snapshot path is intentionally not used."
        )
    entities = pd.read_csv(V2_ENTITIES)
    results = run_benchmark(entities)

    OUT.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUT / "scaling.csv", index=False)
    save_scaling_plot(results, OUT / "scaling.png")
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
