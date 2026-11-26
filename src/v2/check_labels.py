"""Owner script, V2 only. Checks Round 1 labels. UNTESTED.
Usage: python src/v2/check_labels.py"""
import os
import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics import cohen_kappa_score
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")
A, B = "riya", "yashika"
L2V = {"Y": "worth_review", "N": "ordinary", "D": "data_artifact"}
V2L = {v: k for k, v in L2V.items()}

with create_engine(url).connect() as c:
    r = pd.read_sql(text("""SELECT cluster_id, reviewer, verdict FROM reviewer_reviews
        WHERE review_mode='blind_queue' AND review_round='r1'"""), c)
piv = r.pivot_table(index="cluster_id", columns="reviewer", values="verdict", aggfunc="first")
print("reviewers found:", list(piv.columns))
if not {A, B} <= set(piv.columns):
    raise SystemExit("Reviewer names are not riya and yashika. Stop and send me this output.")
piv = piv.dropna(subset=[A, B])
print("clusters reviewed by both:", len(piv))
print("kappa, all four verdicts:", round(cohen_kappa_score(piv[A], piv[B]), 3))
ok = (piv[A] != "need_more_info") & (piv[B] != "need_more_info")
print("kappa, need_more_info excluded:", round(cohen_kappa_score(piv.loc[ok, A], piv.loc[ok, B]), 3),
      "n =", int(ok.sum()))

agreed = ok & (piv[A] == piv[B])
need = piv[~agreed]
print(f"agreed with a usable verdict: {int(agreed.sum())}")
print(f"need adjudication: {len(need)}")
print(sorted(need.index.tolist()))
print("\nneed_more_info involved:")
print(need[(need[A] == "need_more_info") | (need[B] == "need_more_info")].to_string())

# adjudication file
adj = pd.read_csv("results/v2/adjudication.csv")
adj["label"] = adj["label"].astype(str).str.strip().replace({"nan": ""})
adj_map = {int(a): b for a, b in zip(adj.cluster_id, adj.label) if b in L2V}
missing = [int(i) for i in need.index if int(i) not in adj_map]
print("\nclusters needing adjudication with no label yet:", missing)

# final labels file
p = "results/v2/labels_final.csv"
if not os.path.exists(p):
    print("labels_final.csv does not exist yet. Run export_reviews.py after adjudication.")
    raise SystemExit
lab = pd.read_csv(p)
print("labels_final columns:", list(lab.columns))
col = next((x for x in ["final_label", "label", "y"] if x in lab.columns), None)
if col is None:
    raise SystemExit("Tell me which column holds the label.")
fin = {int(a): str(b) for a, b in zip(lab.cluster_id, lab[col])}
bad = []
for cid in agreed.index[agreed]:
    if fin.get(int(cid)) != V2L[piv.loc[cid, A]]:
        bad.append((int(cid), "agreed " + V2L[piv.loc[cid, A]], fin.get(int(cid))))
for cid in need.index:
    want = adj_map.get(int(cid))
    if want is not None and fin.get(int(cid)) != want:
        bad.append((int(cid), "adjudicated " + want, fin.get(int(cid))))
    if want is None and int(cid) in fin:
        bad.append((int(cid), "not adjudicated, but has a final label", fin.get(int(cid))))
print("\nlabel problems:", bad if bad else "none")
print("final label counts:", pd.Series(list(fin.values())).value_counts().to_dict())