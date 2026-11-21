"""Evaluate manually labelled duplicate pairs; labels must be exactly 'y' or 'n'."""
from pathlib import Path

import numpy as np
import pandas as pd

LABELS_PATH = Path("results/v2/pairs_to_label.csv")
FLAGS_PATH = Path("results/v2/pairs_rule_flag.csv")


def _normalized_pair_ids(series, source_name):
    blank_string = series.map(lambda value: isinstance(value, str) and not value.strip())
    if series.isna().any() or blank_string.any():
        raise ValueError(f"{source_name} pair_id values must not be null or blank")
    numeric = pd.to_numeric(series, errors="coerce")
    if (
        numeric.isna().any()
        or not np.isfinite(numeric).all()
        or (numeric <= 0).any()
        or (numeric % 1 != 0).any()
        or (numeric > np.iinfo("int64").max).any()
    ):
        raise ValueError(f"{source_name} pair_id values must be positive integers")
    return numeric.astype("int64")


def evaluate_duplicate_rule(labels, flags):
    """Validate a complete manual sample and return rule precision/near-miss rate."""
    if not {"pair_id", "label"}.issubset(labels.columns):
        raise ValueError("Label file must contain pair_id and label columns")
    if not {"pair_id", "rule_flag"}.issubset(flags.columns):
        raise ValueError("Rule flag file must contain pair_id and rule_flag columns")
    labels = labels.copy()
    flags = flags.copy()
    labels["pair_id"] = _normalized_pair_ids(labels.pair_id, "labels")
    flags["pair_id"] = _normalized_pair_ids(flags.pair_id, "flags")
    if labels.pair_id.duplicated().any() or flags.pair_id.duplicated().any():
        raise ValueError("pair_id values must be unique in both files")
    if labels.empty:
        raise ValueError("No manually labelled pairs were provided")
    if not labels.label.isin(("y", "n")).all():
        invalid = labels.loc[~labels.label.isin(("y", "n")), "label"].tolist()
        raise ValueError(f"Every label must be exactly 'y' or 'n'; invalid values: {invalid[:10]}")
    def valid_rule_flag(value):
        if isinstance(value, (bool, np.bool_)):
            return True
        return isinstance(value, (int, np.integer)) and value in (0, 1)

    if not flags.rule_flag.map(valid_rule_flag).all():
        raise ValueError("rule_flag values must be boolean")

    joined = labels.merge(flags, on="pair_id", how="outer", validate="one_to_one", indicator=True)
    if not joined._merge.eq("both").all():
        raise ValueError("Label and rule-flag files must contain the same pair_id values")
    joined["is_duplicate"] = joined.label.eq("y")
    joined["rule_flag"] = joined.rule_flag.astype(bool)
    flagged = joined[joined.rule_flag]
    unflagged = joined[~joined.rule_flag]

    return {
        "flagged_pairs": len(flagged),
        "true_duplicates_flagged": int(flagged.is_duplicate.sum()),
        "rule_precision": float(flagged.is_duplicate.mean()) if len(flagged) else None,
        "unflagged_near_miss_pairs": len(unflagged),
        "true_duplicates_unflagged": int(unflagged.is_duplicate.sum()),
        "near_miss_positive_rate": float(unflagged.is_duplicate.mean()) if len(unflagged) else None,
    }


def main():
    if not LABELS_PATH.is_file() or not FLAGS_PATH.is_file():
        raise SystemExit(
            "Both manually labelled pairs_to_label.csv and pairs_rule_flag.csv are required. "
            "Complete labels using only exact y/n values before evaluation."
        )
    labels = pd.read_csv(
        LABELS_PATH, keep_default_na=False, usecols=["pair_id", "label"]
    )
    flags = pd.read_csv(FLAGS_PATH, usecols=["pair_id", "rule_flag"])
    result = evaluate_duplicate_rule(labels, flags)
    print(
        "rule-flagged pairs:", result["flagged_pairs"],
        "| truly duplicate:", result["true_duplicates_flagged"],
        "| precision:", result["rule_precision"],
    )
    print(
        "not flagged (sampled near misses):", result["unflagged_near_miss_pairs"],
        "| truly duplicate:", result["true_duplicates_unflagged"],
        "| near-miss positive rate:", result["near_miss_positive_rate"],
    )
    print("The unflagged group is a sampled near-miss pool, not a dataset-wide miss-rate estimate.")


if __name__ == "__main__":
    main()
