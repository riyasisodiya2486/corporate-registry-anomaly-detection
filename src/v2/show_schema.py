import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("V2_DATABASE_URL equals DATABASE_URL. Stop.")
eng = create_engine(url)
insp = inspect(eng)
for t in ["review_queue", "reviewer_reviews"]:
    print("\n" + t)
    for c in insp.get_columns(t):
        print("  ", c["name"], c["type"], "NULL" if c["nullable"] else "NOT NULL")
with eng.connect() as conn:
    for t in ["cleaned_entities", "cluster_assignments", "cluster_scores",
              "cluster_explanations", "review_queue", "reviewer_reviews"]:
        print(t, conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar())