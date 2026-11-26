"""Owner script, V2 only. Publishes human_summary. Needs --approved. UNTESTED.
Usage: python src/v2/create_human_summary.py --approved"""
import os
import sys
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

if "--approved" not in sys.argv:
    raise SystemExit("Run only after Dr. Sahu approved the public human-review line. Add --approved.")
load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")
L2V = {"Y": "worth_review", "N": "ordinary", "D": "data_artifact"}
lab = pd.read_csv("results/v2/labels_final.csv")
col = next((x for x in ["final_label", "label", "y"] if x in lab.columns), None)
if col is None:
    raise SystemExit("Tell me which column holds the label: " + str(list(lab.columns)))
eng = create_engine(url)
with eng.connect() as c:
    rv = pd.read_sql(text("""SELECT cluster_id, reviewer, verdict FROM reviewer_reviews
        WHERE review_mode='blind_queue' AND review_round='r1'"""), c)
agreed = rv.groupby("cluster_id").verdict.nunique().eq(1)
rows = []
for cid, v in zip(lab.cluster_id, lab[col]):
    v = L2V.get(str(v), str(v))
    if v not in L2V.values():
        continue
    rows.append({"cluster_id": int(cid), "final_verdict": v, "n_reviewers": 2,
                 "reviewers_agreed": bool(agreed.get(int(cid), False))})
with eng.begin() as c:
    c.execute(text("""CREATE TABLE IF NOT EXISTS human_summary (
        cluster_id INTEGER PRIMARY KEY REFERENCES cluster_scores(cluster_id),
        final_verdict TEXT NOT NULL CHECK (final_verdict IN ('worth_review','ordinary','data_artifact')),
        n_reviewers INTEGER NOT NULL, reviewers_agreed BOOLEAN NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT now())"""))
    c.execute(text("DELETE FROM human_summary"))
    for r in rows:
        c.execute(text("""INSERT INTO human_summary (cluster_id, final_verdict, n_reviewers, reviewers_agreed)
            VALUES (:cluster_id, :final_verdict, :n_reviewers, :reviewers_agreed)"""), r)
    c.execute(text("GRANT SELECT ON human_summary TO app_reader, app_reviewer"))
print("published", len(rows), "clusters")