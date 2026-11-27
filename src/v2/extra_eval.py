"""Owner script, V2 only. Extra evaluation against the struck-off outcome. UNTESTED.
Usage: python src/v2/extra_eval.py"""
import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy.stats import spearmanr
from sqlalchemy import create_engine, text
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.neighbors import LocalOutlierFactor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MinMaxScaler, StandardScaler

load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")
eng = create_engine(url)
with eng.connect() as c:
    sc = pd.read_sql(text("SELECT * FROM cluster_scores"), c)
    st_ = pd.read_sql(text("""
        SELECT ca.cluster_id,
               COALESCE(BOOL_OR(lower(e.company_status) LIKE 'strike off%'
                             OR lower(e.company_status) LIKE 'under process of striking off%'),
                        FALSE) AS struck
        FROM cluster_assignments ca JOIN cleaned_entities e ON e.entity_id = ca.entity_id
        GROUP BY ca.cluster_id"""), c)

df = sc.merge(st_, on="cluster_id").sort_values("cluster_id").reset_index(drop=True)
y = df["struck"].astype(int).values
print("cluster_scores columns:", list(sc.columns))
FEATURE_COLS = [
    "address_signal_score",
    "name_signal_score",
    "timing_signal_score",
    "capital_similarity_score",
    "topology_score",
    "category_homogeneity_score",
    "bridge_flag",
]
if "bridge_flag" in df.columns:
    df["bridge_flag"] = df["bridge_flag"].astype(int)
feats = [col for col in FEATURE_COLS if col in df.columns]
missing_feats = [col for col in FEATURE_COLS if col not in df.columns]
print("signals used:", feats)
if missing_feats:
    print("Unavailable signals omitted:", missing_feats)
if not feats:
    raise SystemExit("No evaluation signal columns are available.")
X = df[feats].astype(float)
X = X.fillna(X.median()).fillna(0.0)
base = float(y.mean())
print(f"clusters {len(df)}, struck-off base rate {base:.3f}")


def wilson(k, n, z=1.96):
    if n <= 0:
        return np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    m = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return m - h, m + h


def topk(score, K):
    return int(y[np.argsort(-score, kind="stable")[:K]].sum())


def auc_ci(score, B=200, seed=0):
    rng = np.random.default_rng(seed)
    v = []
    for _ in range(B):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() != y[i].max():
            v.append(roc_auc_score(y[i], score[i]))
    return np.percentile(v, 2.5), np.percentile(v, 97.5)


def iforest(cols):
    m = IsolationForest(random_state=42).fit(X[cols])
    return -m.score_samples(X[cols])


systems = {"1 stored composite score": df["composite_score"].values.astype(float),
           "2 Isolation Forest refit, all signals": iforest(feats)}
if len(feats) > 1:
    for f in feats:
        systems[f"3 Isolation Forest without {f}"] = iforest([c for c in feats if c != f])
systems["4 fixed-weight rule (equal weights)"] = MinMaxScaler().fit_transform(X).mean(axis=1)
systems["5 Local Outlier Factor (k=35)"] = -LocalOutlierFactor(n_neighbors=35).fit(
    StandardScaler().fit_transform(X)).negative_outlier_factor_
systems["6 cluster size only"] = df["cluster_size"].values.astype(float)
lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
systems["7 logistic regression, 5-fold (supervised reference)"] = cross_val_predict(
    lr, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=42), method="predict_proba")[:, 1]

rows = []
for name, s in systems.items():
    lo, hi = auc_ci(s)
    r = {"system": name, "AUC": round(roc_auc_score(y, s), 3), "AUC_lo": round(lo, 3), "AUC_hi": round(hi, 3)}
    for K in (50, 100, 370):
        k = topk(s, K)
        a, b = wilson(k, K)
        r.update({f"P@{K}": round(k / K, 3), f"P@{K}_lo": round(a, 3), f"P@{K}_hi": round(b, 3),
                  f"lift@{K}": round((k / K) / base, 2)})
    rows.append(r)
out = pd.DataFrame(rows)
out.to_csv("results/v2/extra_eval_summary.csv", index=False)
print(out[["system", "AUC", "AUC_lo", "AUC_hi", "P@50", "P@100", "P@370", "lift@370"]].to_string(index=False))

srows = []
for label, m in [("size 2", (df.cluster_size == 2).values), ("size 3+", (df.cluster_size >= 3).values)]:
    s = df.loc[m, "composite_score"].values.astype(float)
    srows.append({"stratum": label, "n": int(m.sum()), "base_rate": round(float(y[m].mean()), 3),
                  "metric": "AUC", "value": round(roc_auc_score(y[m], s), 3)})
dqp = "results/v2/cluster_dq.csv"
if os.path.exists(dqp):
    dq = pd.read_csv(dqp)
    artifact_cols = {"artifact", "has_duplicate", "has_placeholder"} & set(dq.columns)
    if artifact_cols:
        dq["art"] = False
        if "artifact" in artifact_cols:
            dq["art"] |= dq["artifact"].fillna(False).astype(bool)
        if "has_duplicate" in artifact_cols:
            dq["art"] |= dq["has_duplicate"].fillna(False).astype(bool)
        if "has_placeholder" in artifact_cols:
            dq["art"] |= dq["has_placeholder"].fillna(False).astype(bool)
        d2 = df.merge(dq[["cluster_id", "art"]], on="cluster_id", how="left")
        keep = ~d2["art"].fillna(False).values
        s, yy = d2.loc[keep, "composite_score"].values.astype(float), y[keep]
        if yy.size and np.unique(yy).size == 2:
            srows.append({"stratum": "artifact-flagged clusters removed", "n": int(keep.sum()),
                          "base_rate": round(float(yy.mean()), 3), "metric": "AUC",
                          "value": round(roc_auc_score(yy, s), 3)})
        for K in (50, 100, 370):
            idx = np.argsort(-s, kind="stable")[:K]
            srows.append({"stratum": "artifact-flagged clusters removed", "n": int(keep.sum()),
                          "base_rate": round(float(yy.mean()), 3), "metric": f"P@{K}",
                          "value": round(float(yy[idx].mean()), 3)})
    else:
        print("cluster_dq.csv columns:", list(dq.columns), "(has_duplicate / has_placeholder not found)")
else:
    print("results/v2/cluster_dq.csv not found; artifact-removed rows skipped (Yashika keeps it local)")
pd.DataFrame(srows).to_csv("results/v2/extra_eval_size.csv", index=False)
print(pd.DataFrame(srows).to_string(index=False))

print("refit vs stored composite, Spearman:", round(spearmanr(systems["2 Isolation Forest refit, all signals"], df["composite_score"])[0], 3))
for label, m in [("size 2", (df.cluster_size == 2).values), ("size 3+", (df.cluster_size >= 3).values)]:
    s_ = df.loc[m, "composite_score"].values.astype(float); yy = y[m]
    for K in (50, 100):
        idx = np.argsort(-s_, kind="stable")[:K]; k = int(yy[idx].sum()); a, b = wilson(k, K)
        print(f"stored score, {label}: P@{K} = {k/K:.3f} ({a:.3f} to {b:.3f}), base rate {yy.mean():.3f}")