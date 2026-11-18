"""Riya. Per-cluster v2 signals from the snapshot. company_status is deliberately NOT loaded:
status is the outside outcome (weak_label_check.py), so it must never be a feature."""
import re
from pathlib import Path

import numpy as np
import pandas as pd

S = Path("results/snapshot")
V2 = Path("results/v2")
V2.mkdir(parents=True, exist_ok=True)
REF_DATE = pd.Timestamp("2026-10-01")
STOP = {"shree", "shri", "sri", "sree", "new", "the", "om", "sai", "m", "s", "mr", "ms"}
VIRTUAL = r"virtual office|co-?working|cowork|business cent(?:er|re)|shared office"
RESID = r"\bc/?o\b|\bflat\b|\bhouse\b|\bh no\b|\bhno\b"

cols = ["entity_id", "company_name_normalized", "address_normalized", "pincode", "nic_code",
        "authorized_capital", "paidup_capital", "date_of_registration"]
ent = pd.read_csv(S / "cleaned_entities.csv", usecols=cols)
asg = pd.read_csv(S / "cluster_assignments.csv")[["entity_id", "cluster_id"]]
sc = pd.read_csv(S / "cluster_scores.csv")[["cluster_id", "cluster_size", "composite_score", "flag_category"]]

pin_counts = ent.pincode.value_counts()
ent["date"] = pd.to_datetime(ent.date_of_registration, errors="coerce")
ent["addr_key"] = (ent.address_normalized.fillna("").astype(str).str.lower()
                      .str.replace(r"[^a-z0-9 ]", " ", regex=True)
                      .str.replace(r"\s+", " ", regex=True).str.strip())
ent["stem"] = ent.company_name_normalized.fillna("").astype(str).str.split().str[0].fillna("")
m = asg.merge(ent, on="entity_id")
addr_clusters = m.groupby("addr_key").cluster_id.nunique()
m["addr_n_clusters"] = m.addr_key.map(addr_clusters)


def modal_share(s, total):
    s = s.dropna()
    return 0.0 if s.empty else float(s.value_counts().iloc[0]) / total


def burst30(dates):
    d = np.sort(dates.dropna().values.astype("datetime64[D]").astype(np.int64))
    if len(d) == 0:
        return 0.0
    hi = np.searchsorted(d, d + 30, side="right")
    return float((hi - np.arange(len(d))).max()) / len(dates)


rows = []
for cid, g in m.groupby("cluster_id"):
    n = len(g)
    span = (g.date.max() - g.date.min()).days if g.date.notna().sum() >= 2 else 0
    auth = pd.to_numeric(g.authorized_capital, errors="coerce")
    paid = pd.to_numeric(g.paidup_capital, errors="coerce")
    ratio = (paid / auth.where(auth > 0)).median()
    stems = g.stem[(g.stem != "") & (~g.stem.isin(STOP))]
    pin = g.pincode.dropna()
    top_pin = pin.value_counts().index[0] if len(pin) else None
    rows.append({
        "cluster_id": cid,
        "same_addr_share": modal_share(g.addr_key.replace("", np.nan), n),
        "addr_crowded_share": float((g.addr_n_clusters >= 3).mean()),
        "burst30_share": burst30(g.date),
        "log_span_days": float(np.log1p(max(span, 0))),
        "name_stem_share": modal_share(stems, n),
        "capital_same_share": modal_share(auth, n),
        "nic_same_share": modal_share(g.nic_code.astype(str).replace("nan", np.nan), n),
        "pincode_same_share": modal_share(pin, n),
        "log_pincode_count": float(np.log1p(pin_counts.get(top_pin, 0))) if top_pin is not None else 0.0,
        "virtual_share": float(g.addr_key.str.contains(VIRTUAL, regex=True).mean()),
        "resid_share": float(g.addr_key.str.contains(RESID, regex=True).mean()),
        "median_age_years": float(((REF_DATE - g.date).dt.days / 365.25).median()) if g.date.notna().any() else 0.0,
        "paidup_ratio": 0.0 if pd.isna(ratio) else float(min(ratio, 1.0)),
    })
f = pd.DataFrame(rows).merge(sc, on="cluster_id")
f["log_size"] = np.log(f.cluster_size)

dq_path = V2 / "cluster_dq.csv"
if dq_path.exists():
    dq = pd.read_csv(dq_path)[["cluster_id", "has_duplicate", "has_placeholder", "artifact"]]
    f = f.merge(dq, on="cluster_id", how="left")
else:
    print("WARNING: results/v2/cluster_dq.csv missing. Run data_quality.py first. Artifact flags set to False.")
    f["has_duplicate"] = f["has_placeholder"] = f["artifact"] = False
for c in ["has_duplicate", "has_placeholder", "artifact"]:
    f[c] = f[c].fillna(False).astype(int)
f.to_csv(V2 / "features_v2.csv", index=False)
print(len(f), "clusters;", f.shape[1], "columns -> results/v2/features_v2.csv")
