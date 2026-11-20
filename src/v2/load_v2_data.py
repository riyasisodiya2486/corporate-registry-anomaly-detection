"""Riya. Loads the FROZEN v1 snapshot (tag results-v1) into the V2 Neon branch. No new dataset is created.
Same 188,042 companies, same 7,384 clusters. Reads only results/snapshot/*.csv. Writes ONLY to V2_DATABASE_URL.
Order matters (foreign keys): entities, scores, assignments, explanations. Tables that already hold rows are skipped."""
import os
import sys

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
v2 = os.environ["V2_DATABASE_URL"]
if v2 == os.environ.get("DATABASE_URL"):
    sys.exit("STOP: V2_DATABASE_URL is the same as DATABASE_URL (production). Fix .env first.")
engine = create_engine(v2)

STEPS = [("cleaned_entities", 2000), ("cluster_scores", 500),
         ("cluster_assignments", 2000), ("cluster_explanations", 2000)]
for table, chunk in STEPS:
    with engine.connect() as conn:
        n = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    if n:
        print(f"{table}: already has {n:,} rows, skipped")
        continue
    df = pd.read_csv(f"results/snapshot/{table}.csv")
    print(f"{table}: inserting {len(df):,} rows ...")
    with engine.begin() as conn:
        df.to_sql(table, conn, if_exists="append", index=False, chunksize=chunk, method="multi")
    print(f"{table}: done")

with engine.connect() as conn:
    for table, _ in STEPS:
        print(table, conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar())
print("Expected: 188,042 / 7,384 / 19,810 / 22,152")