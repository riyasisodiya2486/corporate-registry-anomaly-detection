"""Riya. Round 2 pooled review set: top 20 of each system (excluding Round 1 clusters) plus 20 random clusters.
Raters see only the shuffled cluster list, never which system picked what."""
import pandas as pd

V2 = "results/v2/"
SYS = ["sys_v1", "sys_v1_artifact", "sys_rule", "sys_logreg"]
S = pd.read_csv(V2 + "system_scores.csv")
r1 = set(pd.read_csv(V2 + "label_set_r1.csv").cluster_id)
cand = S[~S.cluster_id.isin(r1)]

member = {}
for c in SYS:
    top = cand.sort_values([c, "cluster_id"], ascending=[False, True]).head(20).cluster_id
    for cid in top:
        member.setdefault(int(cid), []).append(c)
for cid in cand.sample(20, random_state=3).cluster_id:
    member.setdefault(int(cid), []).append("random")

pool = pd.DataFrame({"cluster_id": list(member), "systems": [",".join(v) for v in member.values()]})
pool.to_csv(V2 + "pool_membership.csv", index=False)                 # keep private until evaluation
pool.sample(frac=1, random_state=9)[["cluster_id"]].to_csv(V2 + "label_set_r2.csv", index=False)
print(len(pool), "clusters in the round 2 pool")
