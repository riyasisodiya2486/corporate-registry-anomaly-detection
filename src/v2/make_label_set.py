"""Riya. Round 1 label set: the 40 audited clusters plus 10 new per class. Fixed seeds."""
from pathlib import Path

import pandas as pd

OUT = Path("results/v2")
OUT.mkdir(parents=True, exist_ok=True)

sc = pd.read_csv("results/snapshot/cluster_scores.csv")
old = pd.read_csv("results/audit_sample.csv")[["cluster_id"]]

parts = []
for flag in ["high_priority", "moderate", "baseline"]:
    pool = sc[(sc.flag_category == flag) & (~sc.cluster_id.isin(old.cluster_id))]
    parts.append(pool.sample(min(10, len(pool)), random_state=11))

r1 = pd.concat([old, pd.concat(parts)[["cluster_id"]]]).drop_duplicates()
r1.to_csv(OUT / "label_set_r1.csv", index=False)
print(len(r1), "clusters in round 1")
print(r1.merge(sc[["cluster_id", "flag_category"]], on="cluster_id").flag_category.value_counts())
