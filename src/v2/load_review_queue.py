"""Riya (owner connection from .env). Usage: python src/v2/load_review_queue.py results/v2/label_set_r1.csv r1"""
import os
import sys

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

path, batch = sys.argv[1], sys.argv[2]
ids = pd.read_csv(path).cluster_id.astype(int).unique()

with engine.begin() as conn:
    conn.execute(text("DELETE FROM review_queue WHERE batch = :b"), {"b": batch})
    for c in ids:
        conn.execute(text("INSERT INTO review_queue (cluster_id, batch) VALUES (:c, :b)"),
                     {"c": int(c), "b": batch})
print(len(ids), "clusters queued in batch", batch)
