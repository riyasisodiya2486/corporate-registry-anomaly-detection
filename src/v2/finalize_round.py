"""Owner script, V2 only. Final labels for one review round: agreed, or adjudicated. UNTESTED.
Usage: python src/v2/finalize_round.py r2"""
import os
import sys
import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics import cohen_kappa_score
from sqlalchemy import create_engine, text

rnd = sys.argv[1] if len(sys.argv) > 1 else "r2"
load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")
A, B = "riya", "yashika"
V2L = {"worth_review": "Y", "ordinary": "N", "data_artifact": "D"}
with create_engine(url).connect() as c:
    r = pd.read_sql(text("""SELECT cluster_id, reviewer, verdict FROM reviewer_reviews
        WHERE review_mode='blind_queue' AND review_round=:rd"""), c, params={"rd": rnd})
    q = pd.read_sql(text("SELECT cluster_id FROM review_queue WHERE batch=:rd"), c, params={"rd": rnd})
print("clusters in queue:", len(q), "| reviews per reviewer:", r.groupby("reviewer").cluster_id.nunique().to_dict())
d = r.groupby(["cluster_id", "reviewer"]).size()
if (d > 1).any():
    print("WARNING: duplicate reviews:", d[d > 1].to_dict())
piv = r.pivot_table(index="cluster_id", columns="reviewer", values="verdict", aggfunc="first")
if not {A, B} <= set(piv.columns):
    raise SystemExit("Both reviewers are not present: " + str(list(piv.columns)))
piv = piv.dropna(subset=[A, B])
unfinished = sorted(set(q.cluster_id) - set(piv.index))
if unfinished:
    raise SystemExit(f"Not reviewed by both yet: {unfinished}")
stray = sorted(set(piv.index) - set(q.cluster_id))
if stray:
    print("WARNING: reviews for clusters not in the queue:", stray)
piv = piv.loc[sorted(set(q.cluster_id))]
ok = (piv[A] != "need_more_info") & (piv[B] != "need_more_info")
print("clusters reviewed by both:", len(piv))
print("kappa, all four verdicts:", round(cohen_kappa_score(piv[A], piv[B]), 3))
print("kappa, need_more_info excluded:", round(cohen_kappa_score(piv.loc[ok, A], piv.loc[ok, B]), 3), "n =", int(ok.sum()))
agreed = ok & (piv[A] == piv[B])
both_unsure = (piv[A] == "need_more_info") & (piv[B] == "need_more_info")
need = piv[~agreed & ~both_unsure]
print(f"agreed (usable): {int(agreed.sum())} | both need_more_info: {int(both_unsure.sum())} | need adjudication: {len(need)}")
print("need adjudication:", sorted(need.index.tolist()))

path = f"results/v2/adjudication_{rnd}.csv"
if len(need) and not os.path.exists(path):
    t = pd.DataFrame({"cluster_id": need.index,
                      "riya": [V2L.get(v, v) for v in need[A]],
                      "yashika": [V2L.get(v, v) for v in need[B]], "label": ""})
    t.to_csv(path, index=False)
    raise SystemExit(f"Wrote {path}. Fill the label column (Y, N or D) after the call, then rerun.")
amap = {}
if len(need):
    adj = pd.read_csv(path)
    adj["label"] = adj["label"].astype(str).str.strip().replace({"nan": ""})
    amap = {int(a): b for a, b in zip(adj.cluster_id, adj.label) if b in ("Y", "N", "D")}
    miss = [int(i) for i in need.index if int(i) not in amap]
    if miss:
        raise SystemExit(f"No adjudication label yet for: {miss}")
rows = []
for cid, row in piv.iterrows():
    if agreed.loc[cid]:
        rows.append((int(cid), V2L[row[A]], 2, "agreed"))
    elif both_unsure.loc[cid]:
        rows.append((int(cid), "", 2, "both_unsure"))
    else:
        rows.append((int(cid), amap[int(cid)], 2, "adjudicated"))
out = pd.DataFrame(rows, columns=["cluster_id", "label", "n_raters", "source"])
out.to_csv(f"results/v2/labels_{rnd}.csv", index=False)
print(out.source.value_counts().to_dict(), out.label.value_counts().to_dict(), "total", len(out))