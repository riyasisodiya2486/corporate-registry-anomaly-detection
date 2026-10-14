import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])
out = Path("results/snapshot")
out.mkdir(parents=True, exist_ok=True)

tables = [
    ("cleaned_entities", "entity_id"),
    ("cluster_assignments", "entity_id"),
    ("cluster_scores", "cluster_id"),
    ("cluster_explanations", 'cluster_id, "rank"'),
]
for name, order in tables:
    df = pd.read_sql(f"SELECT * FROM {name} ORDER BY {order}", engine)
    df.to_csv(out / f"{name}.csv", index=False)
    print(f"{name}: {len(df):,} rows")