"""Riya. After round 2 is reviewed and exported: hit rate at 20 per system, with bootstrap intervals."""
import numpy as np
import pandas as pd

V2 = "results/v2/"
SYS = ["sys_v1", "sys_v1_artifact", "sys_rule", "sys_logreg"]
S = pd.read_csv(V2 + "system_scores.csv")
r1 = set(pd.read_csv(V2 + "label_set_r1.csv").cluster_id)
lab = pd.read_csv(V2 + "labels_final.csv").set_index("cluster_id").label
pool = pd.read_csv(V2 + "pool_membership.csv")
cand = S[~S.cluster_id.isin(r1)]
rng = np.random.default_rng(0)


def boot(y, n=5000):
    y = np.asarray(y, dtype=float)
    return np.percentile(rng.choice(y, size=(n, len(y)), replace=True).mean(axis=1), [2.5, 97.5])


groups = {c: cand.sort_values([c, "cluster_id"], ascending=[False, True]).head(20).cluster_id.tolist() for c in SYS}
groups["random"] = [int(c) for c in pool[pool.systems.str.contains("random")].cluster_id]

rows = []
for name, ids in groups.items():
    got = [c for c in ids if c in lab.index]
    if len(got) < len(ids):
        print(f"WARNING: {name}: {len(ids) - len(got)} of {len(ids)} clusters not labelled yet")
    y = [1 if lab[c] == "Y" else 0 for c in got]
    d = [1 if lab[c] == "D" else 0 for c in got]
    lo, hi = boot(y)
    hits = int(sum(y))
    rows.append({"system": name, "n": len(got), "hits": hits, "hit_rate": round(hits / max(len(got), 1), 2),
                 "ci_lo": round(lo, 2), "ci_hi": round(hi, 2),
                 "reviews_per_hit": round(len(got) / hits, 1) if hits else None,
                 "artifact_share_judged": round(sum(d) / max(len(got), 1), 2)})
res = pd.DataFrame(rows)
print(res.to_string(index=False))
res.to_csv(V2 + "pool_eval.csv", index=False)
print("Report intervals. With 20 clusters per system, overlapping intervals mean the difference is not established.")
