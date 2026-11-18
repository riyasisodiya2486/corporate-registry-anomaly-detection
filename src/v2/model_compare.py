"""Riya. Compares ranking systems on Round 1 human labels. Positive class = Y.
A  sys_v1           : v1 Isolation Forest composite score
B  sys_v1_artifact  : v1 score, artifact clusters pushed to the bottom
C  sys_rule         : fixed hand-set weights on v2 features (NOT tuned on labels), artifacts pushed down
D  sys_logreg       : logistic regression on v2 features + v1 score, trained on Round 1 labels
Round 1 has few labels, so A-D are compared by AUC / PR-AUC (D with repeated cross-validation).
The decisive comparison is the pooled top-20 review in Round 2 (pool_round2.py, evaluate_pool.py)."""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

V2 = Path("results/v2")
FEATS = ["same_addr_share", "addr_crowded_share", "burst30_share", "log_span_days", "name_stem_share",
         "capital_same_share", "nic_same_share", "pincode_same_share", "log_pincode_count", "virtual_share",
         "resid_share", "median_age_years", "paidup_ratio", "log_size", "has_duplicate", "has_placeholder", "v1"]

f = pd.read_csv(V2 / "features_v2.csv")
f["v1"] = f.composite_score / 100.0
f["sys_v1"] = f.composite_score
f["sys_v1_artifact"] = f.composite_score - 1000 * f.artifact
f["sys_rule"] = (0.30 * f.same_addr_share * (1 - f.addr_crowded_share) + 0.25 * f.burst30_share
                 + 0.20 * f.name_stem_share + 0.15 * f.capital_same_share + 0.10 * f.nic_same_share
                 ) - 1000 * f.artifact

lab_path = V2 / "labels_final.csv"
if not lab_path.exists():
    raise SystemExit("results/v2/labels_final.csv not found. Run export_reviews.py after round 1 is reviewed.")
lab = pd.read_csv(lab_path)[["cluster_id", "label"]]
d = f.merge(lab, on="cluster_id")
d["y"] = (d.label == "Y").astype(int)
print("labelled:", len(d), "| Y:", int(d.y.sum()), "| base rate:", round(d.y.mean(), 3))
if d.y.nunique() < 2:
    raise SystemExit("Need both Y and non-Y labels.")


def model():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.5, class_weight="balanced", max_iter=2000))


minority = int(min(d.y.sum(), len(d) - d.y.sum()))
k = max(2, min(5, minority))
oof = np.zeros(len(d))
reps = 10
for r in range(reps):
    for tr, te in StratifiedKFold(k, shuffle=True, random_state=r).split(d[FEATS], d.y):
        mdl = model().fit(d.iloc[tr][FEATS], d.y.iloc[tr])
        oof[te] += mdl.predict_proba(d.iloc[te][FEATS])[:, 1] / reps
d["sys_logreg"] = oof

rows = []
for s in ["sys_v1", "sys_v1_artifact", "sys_rule", "sys_logreg"]:
    rows.append({"system": s, "roc_auc": round(roc_auc_score(d.y, d[s]), 3),
                 "pr_auc": round(average_precision_score(d.y, d[s]), 3)})
res = pd.DataFrame(rows)
print(res.to_string(index=False))
print("(sys_logreg is out-of-fold; the others use no training)")
res.to_csv(V2 / "model_compare_round1.csv", index=False)

final = model().fit(d[FEATS], d.y)
f["sys_logreg"] = final.predict_proba(f[FEATS])[:, 1]
f[["cluster_id", "sys_v1", "sys_v1_artifact", "sys_rule", "sys_logreg", "artifact"]].to_csv(
    V2 / "system_scores.csv", index=False)
coef = pd.Series(final[-1].coef_[0], index=FEATS).sort_values(key=abs, ascending=False)
print("\nLargest logistic coefficients (standardised):")
print(coef.head(8).round(3).to_string())
