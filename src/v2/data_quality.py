"""Duplicate-record and placeholder-address analysis for explicit V2 inputs."""
import argparse
import os
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

import pandas as pd

NAME_RATIO = 0.92
DATE_DAYS = 3
MIN_ADDR_CLUSTERS = 3
VIRTUAL = r"virtual office|co-?working|cowork|business cent(?:er|re)|shared office"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "v2"
INPUT_FILES = ("cleaned_entities.csv", "cluster_assignments.csv", "cluster_scores.csv")
ENTITY_COLUMNS = {
    "entity_id",
    "company_name_normalized",
    "pincode",
    "date_of_registration",
}
ASSIGNMENT_COLUMNS = {"entity_id", "cluster_id"}
SCORE_COLUMNS = {"cluster_id", "flag_category", "composite_score"}


def validate_input_dir(input_dir):
    """Validate a V2 input directory using headers only; never choose V1 implicitly."""
    input_dir = Path(input_dir).expanduser()
    resolved = input_dir.resolve()
    results_root = (PROJECT_ROOT / "results").resolve()
    try:
        relative_to_results = resolved.relative_to(results_root)
    except ValueError:
        relative_to_results = None
    if relative_to_results and (
        relative_to_results.parts[0] == "snapshot"
        or relative_to_results.parts[0].startswith("snapshot_backup_")
    ):
        raise ValueError("V1 snapshot and backup directories cannot be used as V2 input")

    paths = {name: input_dir / name for name in INPUT_FILES}
    missing_files = [str(path) for path in paths.values() if not path.is_file()]
    if missing_files:
        raise FileNotFoundError("Missing required V2 input file(s): " + ", ".join(missing_files))

    headers = {name: set(pd.read_csv(path, nrows=0).columns) for name, path in paths.items()}
    address_column = next(
        (column for column in ("address_normalized", "address_raw")
         if column in headers["cleaned_entities.csv"]),
        None,
    )
    required_by_file = {
        "cleaned_entities.csv": ENTITY_COLUMNS,
        "cluster_assignments.csv": ASSIGNMENT_COLUMNS,
        "cluster_scores.csv": SCORE_COLUMNS,
    }
    missing_columns = {
        filename: sorted(required - headers[filename])
        for filename, required in required_by_file.items()
        if required - headers[filename]
    }
    if address_column is None:
        missing_columns["cleaned_entities.csv"] = sorted(
            set(missing_columns.get("cleaned_entities.csv", []))
            | {"address_normalized or address_raw"}
        )
    if missing_columns:
        details = "; ".join(f"{name}: {columns}" for name, columns in missing_columns.items())
        raise ValueError("Missing required V2 column(s): " + details)
    return paths, address_column


def load_inputs(input_dir):
    """Validate all input files before loading their full contents."""
    paths, address_column = validate_input_dir(input_dir)
    entities = pd.read_csv(
        paths["cleaned_entities.csv"],
        usecols=["entity_id", "company_name_normalized", address_column,
                 "pincode", "date_of_registration"],
    )
    assignments = pd.read_csv(
        paths["cluster_assignments.csv"], usecols=["entity_id", "cluster_id"]
    )
    scores = pd.read_csv(
        paths["cluster_scores.csv"],
        usecols=["cluster_id", "flag_category", "composite_score"],
    )
    return entities, assignments, scores, address_column


def analyze_data_quality(entities, assignments, scores, address_column):
    """Compute duplicate and placeholder indicators without reading or writing files."""
    merged = assignments.merge(entities, on="entity_id")
    merged["date"] = pd.to_datetime(merged.date_of_registration, errors="coerce")
    merged["addr_key"] = (
        merged[address_column].fillna("").astype(str).str.lower()
        .str.replace(r"[^a-z0-9 ]", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True).str.strip()
    )

    address_clusters = merged.groupby("addr_key").cluster_id.nunique()
    merged["addr_clusters"] = merged.addr_key.map(address_clusters)
    zero_pin = pd.to_numeric(merged.pincode, errors="coerce").fillna(0) == 0
    merged["placeholder"] = (
        (merged.addr_clusters >= MIN_ADDR_CLUSTERS)
        | zero_pin
        | merged.addr_key.str.startswith("na ")
        | merged.addr_key.eq("")
    )
    merged["virtual_kw"] = merged.addr_key.str.contains(VIRTUAL, regex=True)

    duplicate_rows = []
    for cluster_id, group in merged.groupby("cluster_id"):
        items = list(
            group[["entity_id", "company_name_normalized", "date"]]
            .itertuples(index=False)
        )
        for first, second in combinations(items, 2):
            if pd.isna(first.date) or pd.isna(second.date):
                continue
            if abs((first.date - second.date).days) > DATE_DAYS:
                continue
            name_a, name_b = str(first.company_name_normalized), str(second.company_name_normalized)
            ratio = 1.0 if name_a == name_b else SequenceMatcher(None, name_a, name_b).ratio()
            if ratio >= NAME_RATIO:
                duplicate_rows.append({
                    "cluster_id": cluster_id,
                    "entity_a": first.entity_id,
                    "entity_b": second.entity_id,
                    "name_ratio": round(ratio, 3),
                })
    duplicates = pd.DataFrame(
        duplicate_rows, columns=["cluster_id", "entity_a", "entity_b", "name_ratio"]
    )

    cluster_flags = merged.groupby("cluster_id").agg(
        has_placeholder=("placeholder", "any"),
        virtual_share=("virtual_kw", "mean"),
        max_addr_clusters=("addr_clusters", "max"),
    ).reset_index()
    quality = scores.merge(cluster_flags, on="cluster_id", how="left")
    duplicate_counts = duplicates.groupby("cluster_id").size()
    quality["n_dup_pairs"] = quality.cluster_id.map(duplicate_counts).fillna(0).astype(int)
    quality["has_duplicate"] = quality.n_dup_pairs > 0
    quality["artifact"] = quality.has_duplicate | quality.has_placeholder.fillna(False)
    return duplicates, quality, address_clusters


def run_data_quality(input_dir, output_dir=DEFAULT_OUTPUT_DIR):
    """Validate, analyze, and write local V2 outputs."""
    entities, assignments, scores, address_column = load_inputs(input_dir)
    duplicates, quality, address_clusters = analyze_data_quality(
        entities, assignments, scores, address_column
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    duplicates.to_csv(output_dir / "dup_pairs.csv", index=False)
    quality.to_csv(output_dir / "cluster_dq.csv", index=False)
    (address_clusters.sort_values(ascending=False).head(50).rename("clusters")
     .reset_index().to_csv(output_dir / "placeholder_top50.csv", index=False))

    summary = quality.groupby("flag_category").agg(
        clusters=("cluster_id", "size"),
        duplicate=("has_duplicate", "sum"),
        placeholder=("has_placeholder", "sum"),
        artifact=("artifact", "sum"),
    )
    summary["artifact_pct"] = (100 * summary.artifact / summary.clusters).round(1)
    print(summary)
    return summary


def load_inputs_from_db(database_url=None):
    """Load V2 tables directly via V2_DATABASE_URL; refuse if equal to DATABASE_URL."""
    v2_url = (database_url or os.environ.get('V2_DATABASE_URL') or '').strip()
    if not v2_url:
        raise ValueError('V2_DATABASE_URL is not set')
    prod_url = (os.environ.get('DATABASE_URL') or '').strip()
    if prod_url and v2_url == prod_url:
        raise RuntimeError('Refusing to run V2 data quality against DATABASE_URL (production)')
    from sqlalchemy import create_engine
    engine = create_engine(v2_url)
    try:
        with engine.connect() as conn:
            cols_res = pd.read_sql("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='cleaned_entities'", conn)
            entity_cols = set(cols_res['column_name'].tolist())
            addr_col = 'address_normalized' if 'address_normalized' in entity_cols else ('address_raw' if 'address_raw' in entity_cols else None)
            if addr_col is None:
                raise ValueError('Missing address_normalized or address_raw in cleaned_entities')
            entities = pd.read_sql(f'SELECT entity_id, company_name_normalized, {addr_col}, pincode, date_of_registration FROM cleaned_entities', conn)
            assignments = pd.read_sql('SELECT entity_id, cluster_id FROM cluster_assignments', conn)
            scores = pd.read_sql('SELECT cluster_id, flag_category, composite_score FROM cluster_scores', conn)
    finally:
        engine.dispose()
    return entities, assignments, scores, addr_col


def run_data_quality_from_db(output_dir=DEFAULT_OUTPUT_DIR, database_url=None):
    entities, assignments, scores, address_column = load_inputs_from_db(database_url)
    duplicates, quality, address_clusters = analyze_data_quality(entities, assignments, scores, address_column)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    duplicates.to_csv(output_dir / 'dup_pairs.csv', index=False)
    quality.to_csv(output_dir / 'cluster_dq.csv', index=False)
    (address_clusters.sort_values(ascending=False).head(50).rename('clusters').reset_index().to_csv(output_dir / 'placeholder_top50.csv', index=False))
    summary = quality.groupby('flag_category').agg(clusters=('cluster_id', 'size'), duplicate=('has_duplicate', 'sum'), placeholder=('has_placeholder', 'sum'), artifact=('artifact', 'sum'))
    summary['artifact_pct'] = (100 * summary.artifact / summary.clusters).round(1)
    print(summary)
    return summary

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        default=os.environ.get("V2_INPUT_DIR"),
        help="directory containing the three isolated V2 CSV inputs (or set V2_INPUT_DIR)",
    )
    parser.add_argument(
        "--from-db",
        action="store_true",
        help="load directly from V2_DATABASE_URL instead of a CSV directory",
    )
    args = parser.parse_args(argv)
    if args.from_db:
        run_data_quality_from_db()
        return
    if not args.input_dir:
        parser.error("provide --input-dir or set V2_INPUT_DIR; results/snapshot is never used")
    run_data_quality(args.input_dir)


if __name__ == "__main__":
    main()
