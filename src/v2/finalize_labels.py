"""Owner script, V2 only. Final Round 1 labels: agreed, or adjudicated. UNTESTED."""
import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")
A, B = "riya", "yashika"
V2L = {"worth_review": "Y", "ordinary": "N", "data_artifact": "D"}
with create_engine(url).connect() as c:
    r = pd.read_sql(text("""SELECT cluster_id, reviewer, verdict FROM reviewer_reviews
        WHERE review_mode='blind_queue' AND review_round='r1'"""), c)
piv = r.pivot_table(index="cluster_id", columns="reviewer", values="verdict",
                    aggfunc="first").dropna(subset=[A, B])
adj = pd.read_csv("results/v2/adjudication.csv")
adj["label"] = adj["label"].astype(str).str.strip().replace({"nan": ""})
amap = {int(a): b for a, b in zip(adj.cluster_id, adj.label) if b in ("Y", "N", "D")}
rows, missing = [], []
for cid, row in piv.iterrows():
    if row[A] == row[B] and row[A] in V2L:
        rows.append((int(cid), V2L[row[A]], 2, "agreed"))
    elif int(cid) in amap:
        rows.append((int(cid), amap[int(cid)], 2, "adjudicated"))
    else:
        missing.append(int(cid))
if missing:
    print("NOT FINAL, no adjudication label for:", missing)
out = pd.DataFrame(rows, columns=["cluster_id", "label", "n_raters", "source"]).sort_values("cluster_id")
out.to_csv("results/v2/labels_final.csv", index=False)
print(out.source.value_counts().to_dict(), out.label.value_counts().to_dict(), "total", len(out))