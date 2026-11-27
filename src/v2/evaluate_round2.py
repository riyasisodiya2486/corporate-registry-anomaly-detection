"""Owner script, V2 only. Round 2: hit rate at 20 per ranking system. UNTESTED.
Usage: python src/v2/evaluate_round2.py"""
import numpy as np
import pandas as pd

V2 = "results/v2/"
SYS = ["sys_v1", "sys_v1_artifact", "sys_rule", "sys_logreg"]
sc = pd.read_csv(V2 + "system_scores.csv")
print("system_scores columns:", list(sc.columns))
if not set(SYS + ["cluster_id", "artifact"]) <= set(sc.columns):
    raise SystemExit("Expected columns missing. Send me the column list above.")
sc["cluster_id"] = sc["cluster_id"].astype(int)
pool = set(pd.read_csv(V2 + "label_set_r2.csv").cluster_id.astype(int))
r1 = set(pd.read_csv(V2 + "labels_final.csv").cluster_id.astype(int))
l2 = pd.read_csv(V2 + "labels_r2.csv")
l2["label"] = l2["label"].fillna("").astype(str).str.strip()
lab2 = dict(zip(l2.cluster_id.astype(int), l2.label))
cand = sc[~sc.cluster_id.isin(r1)]
tops = {s: cand.sort_values([s, "cluster_id"], ascending=[False, True]).head(20).cluster_id.tolist() for s in SYS}
U = set().union(*tops.values())
print(f"pool {len(pool)} | union of rebuilt top-20 lists {len(U)} | in pool but not in any top-20: {len(pool - U)}")
if not U <= pool:
    raise SystemExit("MISMATCH: rebuilt top-20 clusters that are not in the reviewed pool: "
                     + str(sorted(U - pool)) + ". Send me this and pool_round2.py.")
randoms = sorted(pool - U)


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    m = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return m - h, m + h


def usable(ids):
    return [lab2[i] for i in ids if lab2.get(i) in ("Y", "N", "D")]


rows = []
for name, ids in list(tops.items()) + [("random group", randoms), ("all reviewed", sorted(pool))]:
    u = usable(ids)
    n, k = len(u), sum(x == "Y" for x in u)
    dart = sum(x == "D" for x in u)
    lo, hi = wilson(k, n)
    rows.append({"group": name, "clusters": len(ids), "labelled": n, "worth_review": k,
                 "hit_rate": round(k / n, 3) if n else None, "lo": round(lo, 3), "hi": round(hi, 3),
                 "data_artifact": dart, "reviews_per_hit": round(n / k, 1) if k else None})
out = pd.DataFrame(rows)
out.to_csv(V2 + "round2_eval.csv", index=False)
print(out.to_string(index=False))

rng = np.random.default_rng(0)
hv = lambda ids: np.array([1 if x == "Y" else 0 for x in usable(ids)])
base = hv(tops["sys_v1"])
for s in SYS[1:]:
    a = hv(tops[s])
    diffs = [rng.choice(a, len(a)).mean() - rng.choice(base, len(base)).mean() for _ in range(5000)]
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    print(f"{s} minus sys_v1: hit rate {a.mean():.3f} vs {base.mean():.3f}, difference {a.mean()-base.mean():+.3f} "
          f"(bootstrap 95% {lo:+.3f} to {hi:+.3f}); shared clusters: {len(set(tops[s]) & set(tops['sys_v1']))}")
a, b = hv(tops["sys_v1_artifact"]), base
print("PRE-STATED TEST (artifact-aware system above v1 at 20):", "PASS" if a.mean() > b.mean() else "FAIL",
      f"({a.mean():.3f} vs {b.mean():.3f})")

art = pd.to_numeric(sc["artifact"], errors="coerce").fillna(0) > 0
print("\nartifact share in the top 370 of each system (definition = the 'artifact' column of system_scores.csv):")
for s in SYS:
    t = sc.assign(art=art).sort_values([s, "cluster_id"], ascending=[False, True]).head(370)
    print(f"  {s}: {t.art.mean():.3f}")

m = pd.read_csv(V2 + "labels_final.csv").merge(sc[["cluster_id", "artifact"]], on="cluster_id")
m["flag"] = pd.to_numeric(m["artifact"], errors="coerce").fillna(0) > 0
print("\nRound 1 human labels (70) vs the artifact flag:")
print(pd.crosstab(m.label, m.flag, rownames=["human label"], colnames=["artifact flag"]))
m2 = l2[l2.label.isin(["Y", "N", "D"])].merge(sc[["cluster_id", "artifact"]], on="cluster_id")
m2["flag"] = pd.to_numeric(m2["artifact"], errors="coerce").fillna(0) > 0
print("Round 2 human labels vs the artifact flag:")
print(pd.crosstab(m2.label, m2.flag, rownames=["human label"], colnames=["artifact flag"]))
print("\nNote: about 20 clusters per system, so intervals are wide. Bootstrap differences ignore overlap and are conservative.")