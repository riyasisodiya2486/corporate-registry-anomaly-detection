"""Owner script, V2 only. Agreement of AI verdicts with human labels. UNTESTED.
Usage: python src/v2/ai_agreement.py"""
import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics import cohen_kappa_score
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")
L2V = {"Y": "worth_review", "N": "ordinary", "D": "data_artifact"}


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    m = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return m - h, m + h


def report(name, h, a):
    d = pd.DataFrame({"h": h, "a": a})
    d = d[(d.h != "need_more_info") & (d.a != "need_more_info")]
    if len(d) < 2:
        print(name, ": not enough pairs")
        return
    k = int((d.h == d.a).sum())
    lo, hi = wilson(k, len(d))
    print(f"{name}: exact agreement {k}/{len(d)} = {k/len(d):.3f} (95% interval {lo:.3f} to {hi:.3f}), "
          f"kappa {cohen_kappa_score(d.h, d.a):.3f}")
    wr = (d.h == "worth_review") == (d.a == "worth_review")
    k2 = int(wr.sum())
    lo, hi = wilson(k2, len(d))
    print(f"   worth_review versus not: {k2}/{len(d)} = {k2/len(d):.3f} ({lo:.3f} to {hi:.3f})")
    print(pd.crosstab(d.h, d.a, rownames=["human"], colnames=["AI"]).to_string())


eng = create_engine(url)
with eng.connect() as c:
    ai = pd.read_sql(text("SELECT cluster_id, verdict AS ai FROM ai_opinions"), c).set_index("cluster_id")
    rv = pd.read_sql(text("""SELECT cluster_id, reviewer, verdict FROM reviewer_reviews
        WHERE review_mode='blind_queue' AND review_round='r1'"""), c)
piv = rv.pivot_table(index="cluster_id", columns="reviewer", values="verdict", aggfunc="first")
for who in ["riya", "yashika"]:
    j = piv[[who]].join(ai, how="inner")
    print(f"\n=== AI versus {who} (clusters with both: {len(j)}) ===")
    report(who, j[who], j["ai"])

p = "results/v2/labels_final.csv"
if os.path.exists(p):
    lab = pd.read_csv(p)
    col = next((x for x in ["final_label", "label", "y"] if x in lab.columns), None)
    if col:
        lab["human"] = lab[col].astype(str).map(lambda v: L2V.get(v, v))
        j = lab[["cluster_id", "human"]].set_index("cluster_id").join(ai, how="inner")
        print(f"\n=== AI versus adjudicated labels (n with both: {len(j)}) ===")
        report("adjudicated", j["human"], j["ai"])
        j.reset_index().to_csv("results/v2/ai_vs_human.csv", index=False)
else:
    print("labels_final.csv not found yet; only per-rater results shown")