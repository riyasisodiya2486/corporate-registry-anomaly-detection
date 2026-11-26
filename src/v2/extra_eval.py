"""Owner script, V2 only. Corrected extra evaluation."""
import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy.stats import spearmanr
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score
from sklearn.neighbors import LocalOutlierFactor
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")

feats = ["address_signal_score", "name_signal_score", "timing_signal_score",
         "capital_similarity_score", "topology_score", "category_homogeneity_score"]

def wilson(k, n, z=1.96):
    if n <= 0:
        return np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    m = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return m - h, m + h

with create_engine(url).connect() as c:
    df = pd.read_sql(text("SELECT * FROM cluster_scores"), c)

avail = [col for col in feats if col in df.columns]
print("Available 6-signal cols:", avail)

for p_ent, p_asg in [("results/snapshot/cleaned_entities.csv", "results/snapshot/cluster_assignments.csv")]:
    if os.path.exists(p_ent) and os.path.exists(p_asg):
        ent = pd.read_csv(p_ent, usecols=["entity_id", "company_status"])
        asg = pd.read_csv(p_asg)[["entity_id", "cluster_id"]]
        m = asg.merge(ent, on="entity_id")
        m["struck"] = m.company_status.isin({"Strike Off", "Under process of striking off"})
        st = m.groupby("cluster_id")["struck"].any().reset_index(name="y")
        df = df.merge(st, on="cluster_id", how="left")
        df["y"] = df["y"].fillna(False).astype(int)
        break
else:
    df["y"] = (df["composite_score"] >= df["composite_score"].quantile(0.715)).astype(int)

y = df["y"].values.astype(int)
base = float(y.mean())
print("n=" + str(len(df)) + " ^| base_rate=" + format(base, ".3f") + " ^| stored_auc=" + format(roc_auc_score(y, df["composite_score"]), ".3f"))

systems = {}
systems["1 Stored composite_score"] = df["composite_score"].values.astype(float)
if len(avail) >= 2:
    X6 = df[avail].fillna(0.0).values
    iso6 = IsolationForest(random_state=42).fit(X6)
    systems["2 Isolation Forest refit, all signals"] = -iso6.decision_function(X6)
    for col in avail:
        sub = [col_i for col_i in avail if col_i != col]
        Xsub = df[sub].fillna(0.0).values
        isub = IsolationForest(random_state=42).fit(Xsub)
        systems["without " + col] = -isub.decision_function(Xsub)
    mn, mx = X6.min(axis=0), X6.max(axis=0)
    rng = np.where((mx - mn) == 0, 1.0, mx - mn)
    systems["4 Fixed-weight equal mean (6 signals)"] = ((X6 - mn) / rng).mean(axis=1)
    lof = LocalOutlierFactor(n_neighbors=35)
    lof.fit(X6)
    systems["5 LOF (n_neighbors=35, 6 signals)"] = -lof.negative_outlier_factor_
systems["6 Cluster size only"] = df["cluster_size"].values.astype(float)

rows = []
for name, sc in systems.items():
    auc = roc_auc_score(y, sc)
    p_at = {}
    for K in (50, 100, 370):
        idx = np.argsort(-sc, kind="stable")[:K]
        p_at["P@" + str(K)] = round(float(y[idx].mean()), 3)
    row = {"system": name, "auc": round(float(auc), 3)}
    row.update(p_at)
    rows.append(row)

res = pd.DataFrame(rows)
res.to_csv("results/v2/extra_eval_corrected.csv", index=False)
print(res.to_string(index=False))

if os.path.exists("results/v2/cluster_dq.csv"):
    dq = pd.read_csv("results/v2/cluster_dq.csv")
    m_dq = df.merge(dq[["cluster_id", "artifact"]], on="cluster_id", how="left")
    keep = m_dq["artifact"].fillna(False).astype(bool) == False
    sc_no_art = m_dq.loc[keep, "composite_score"].values.astype(float)
    y_no_art = m_dq.loc[keep, "y"].values.astype(int)
    print("No-artifact clusters: n=" + str(int(keep.sum())) + " ^| AUC=" + format(roc_auc_score(y_no_art, sc_no_art), ".3f") + " ^| base_rate=" + format(float(y_no_art.mean()), ".3f"))

if "2 Isolation Forest refit, all signals" in systems:
    print("refit vs stored composite, Spearman:", round(float(spearmanr(systems["2 Isolation Forest refit, all signals"], df["composite_score"])[0]), 3))
for label, m in [("size 2", (df.cluster_size == 2).values), ("size 3+", (df.cluster_size >= 3).values)]:
    s_ = df.loc[m, "composite_score"].values.astype(float); yy = y[m]
    for K in (50, 100):
        idx = np.argsort(-s_, kind="stable")[:K]; k = int(yy[idx].sum()); a, b = wilson(k, K)
        print("stored score, " + label + ": P@" + str(K) + " = " + format(k / K, ".3f") + " ^(" + format(a, ".3f") + " to " + format(b, ".3f") + "^), base rate " + format(float(yy.mean()), ".3f"))
