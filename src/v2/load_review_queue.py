"""Riya. Usage: python src/v2/load_review_queue.py results/v2/label_set_r1.csv r1
Writes to V2 only."""
import os
import sys

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")
engine = create_engine(url)

path, batch = sys.argv[1], sys.argv[2]
ids = pd.read_csv(path).cluster_id.astype(int).unique()

with engine.begin() as conn:
    conn.execute(text("DELETE FROM review_queue WHERE batch = :b"), {"b": batch})
    for c in ids:
        conn.execute(text("INSERT INTO review_queue (cluster_id, batch) VALUES (:c, :b)"),
                     {"c": int(c), "b": batch})
print(len(ids), "clusters queued in batch", batch, "(V2)")