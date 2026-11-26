"""Owner script, V2 only. Do higher tiers contain more clusters judged worth review? UNTESTED."""
import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics import roc_auc_score
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    m = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return m - h, m + h


lab = pd.read_csv("results/v2/labels_final.csv")
with create_engine(url).connect() as c:
    s = pd.read_sql(text("SELECT cluster_id, cluster_size, composite_score, flag_category FROM cluster_scores"), c)
d = lab.merge(s, on="cluster_id")
print("labelled clusters:", len(d), "| by tier:", d.flag_category.value_counts().to_dict())
rows = []
for tier in ["high_priority", "moderate", "baseline"]:
    g = d[d.flag_category == tier]
    n = len(g)
    for name, code in [("worth_review", "Y"), ("data_artifact", "D"), ("ordinary", "N")]:
        k = int((g.label == code).sum())
        lo, hi = wilson(k, n) if n else (np.nan, np.nan)
        rows.append({"tier": tier, "n": n, "verdict": name, "k": k,
                     "rate": round(k / n, 3) if n else None, "lo": round(lo, 3), "hi": round(hi, 3)})
out = pd.DataFrame(rows)
out.to_csv("results/v2/tier_vs_human.csv", index=False)
print(out.to_string(index=False))
y = (d.label == "Y").astype(int)
if y.nunique() == 2:
    print("AUC of stored score for 'worth_review' vs not:", round(roc_auc_score(y, d.composite_score), 3), "n =", len(d))
print("Note: the sample is stratified (30/10/30), so tier rates are comparable. Intervals are wide.")