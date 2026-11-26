"""Riya (owner connection). Exports reviews, prints Cohen's kappa, writes results/v2/labels_final.csv.
Positive class = Y (worth a closer look). D (data artifact) and N count as not worth review.
Ties between raters stay unresolved until you fill results/v2/adjudication.csv (cluster_id,label)."""
import os
from itertools import combinations
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics import cohen_kappa_score
from sqlalchemy import create_engine

load_dotenv(".env")
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")
engine = create_engine(url)

Path("results/review").mkdir(parents=True, exist_ok=True)
OUT = Path("results/v2")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_sql("SELECT * FROM reviewer_reviews ORDER BY review_id", engine)
df.to_csv("results/review/reviews_raw.csv", index=False)           # private: has notes, in .gitignore

codes = {"worth_review": "Y", "ordinary": "N", "data_artifact": "D"}
b = (df[df.review_mode == "blind_queue"].sort_values("review_id")
       .drop_duplicates(["cluster_id", "reviewer"], keep="last"))
b = b[b.verdict.isin(codes)].assign(label=lambda d: d.verdict.map(codes))
wide = b.pivot(index="cluster_id", columns="reviewer", values="label")
both_count = int((wide.notna().sum(axis=1) >= 2).sum())
print("clusters reviewed by >=2 raters:", both_count)

rows = []
for a, c in combinations(wide.columns, 2):
    j = wide[[a, c]].dropna()
    if len(j) >= 5:
        k = cohen_kappa_score(j[a], j[c])
        rows.append({"rater_a": a, "rater_b": c, "kappa": round(k, 3), "n": len(j)})
        print(a, c, "kappa", round(k, 3), "n", len(j))
pd.DataFrame(rows).to_csv(OUT / "kappa.csv", index=False)


def majority(row):
    vc = row.dropna().value_counts()
    if vc.empty:
        return None
    if len(vc) > 1 and vc.iloc[0] == vc.iloc[1]:
        return None
    return vc.index[0]


final = wide.apply(majority, axis=1).rename("label").to_frame()
final["n_raters"] = wide.notna().sum(axis=1)
unresolved = final[final.label.isna()]
print("unresolved (need adjudication):", len(unresolved), list(unresolved.index)[:30])

adj_path = OUT / "adjudication.csv"
if not adj_path.exists() and len(unresolved) > 0:
    starter = wide.loc[unresolved.index].reset_index()
    starter["label"] = ""
    starter.to_csv(adj_path, index=False)
    print("wrote starter adjudication template:", adj_path)

if adj_path.exists():
    adj = pd.read_csv(adj_path).dropna(subset=["label"])
    adj = adj[adj["label"].astype(str).str.strip() != ""].set_index("cluster_id")["label"]
    final.loc[final.index.intersection(adj.index), "label"] = adj

still_unresolved = final[final.label.isna()]
print("still unresolved after adjudication.csv:", len(still_unresolved))
final = final.dropna(subset=["label"]).reset_index()
final.to_csv(OUT / "labels_final.csv", index=False)          # no names: safe to commit
print(final.label.value_counts())
