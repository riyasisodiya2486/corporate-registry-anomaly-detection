"""Riya. Outside outcome check: do higher-flag clusters hold more struck-off companies?
Status is NOT a model feature, so this is not circular. Strike-off means non-compliance, not 'shell'."""
from math import sqrt
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

S = Path("results/snapshot")
OUT = Path("results/v2")
OUT.mkdir(parents=True, exist_ok=True)
STRUCK = {"Strike Off", "Under process of striking off"}
EFILING = {"Inactive for e-filing"}

ent = pd.read_csv(S / "cleaned_entities.csv", usecols=["entity_id", "company_status"])
asg = pd.read_csv(S / "cluster_assignments.csv")[["entity_id", "cluster_id"]]
sc = pd.read_csv(S / "cluster_scores.csv")[["cluster_id", "cluster_size", "flag_category", "composite_score"]]
m = asg.merge(ent, on="entity_id")
m["struck"] = m.company_status.isin(STRUCK)
m["efil"] = m.company_status.isin(EFILING)
c = m.groupby("cluster_id").agg(n=("struck", "size"), n_struck=("struck", "sum"), n_efil=("efil", "sum")).reset_index()
c["any_struck"] = c.n_struck > 0
c["any_efil"] = c.n_efil > 0
d = sc.merge(c, on="cluster_id")


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


rows = []
for outcome in ["any_struck", "any_efil"]:
    for size_label, g0 in [("all", d), ("size 2", d[d.cluster_size == 2]), ("size 3+", d[d.cluster_size >= 3])]:
        for flag in ["high_priority", "moderate", "baseline"]:
            g = g0[g0.flag_category == flag]
            k, n = int(g[outcome].sum()), len(g)
            lo, hi = wilson(k, n)
            rows.append({"outcome": outcome, "size": size_label, "flag": flag, "k": k, "n": n,
                         "pct": round(100 * k / max(n, 1), 1), "lo": round(100 * lo, 1), "hi": round(100 * hi, 1)})
res = pd.DataFrame(rows)
print(res.to_string(index=False))
res.to_csv(OUT / "weak_label_ci.csv", index=False)

print("\nAUC of composite_score against 'any member struck off'")
print("all:", round(roc_auc_score(d.any_struck, d.composite_score), 3))
for s in (2, 3):
    g = d[d.cluster_size == s]
    if g.any_struck.nunique() == 2:
        print(f"size {s}:", round(roc_auc_score(g.any_struck, g.composite_score), 3), "n =", len(g))
