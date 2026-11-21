import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

print("Loading cluster scores...")
scores_df = pd.read_csv("results/snapshot/cluster_scores.csv")

with engine.begin() as conn:
    print(f"Inserting {len(scores_df)} rows into cluster_scores in chunks...")
    scores_df.to_sql("cluster_scores", conn, if_exists="append", index=False, chunksize=500)
    print("cluster_scores loaded successfully!")

print("Base cluster scores populated successfully!")