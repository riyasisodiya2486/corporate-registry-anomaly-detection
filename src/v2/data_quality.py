"""Yashika. Duplicate-record and placeholder-address flags per cluster. Thresholds fixed before looking."""
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

import pandas as pd

NAME_RATIO = 0.92
DATE_DAYS = 3
MIN_ADDR_CLUSTERS = 3
VIRTUAL = r"virtual office|co-?working|cowork|business cent(?:er|re)|shared office"

S = Path("results/snapshot")
OUT = Path("results/v2")
OUT.mkdir(parents=True, exist_ok=True)

header = pd.read_csv(S / "cleaned_entities.csv", nrows=0).columns
addr_col = "address_normalized" if "address_normalized" in header else "address_raw"
ent = pd.read_csv(S / "cleaned_entities.csv",
                  usecols=["entity_id", "company_name_normalized", addr_col, "pincode", "date_of_registration"])
asg = pd.read_csv(S / "cluster_assignments.csv")[["entity_id", "cluster_id"]]
sc = pd.read_csv(S / "cluster_scores.csv")[["cluster_id", "flag_category", "composite_score"]]

m = asg.merge(ent, on="entity_id")
m["date"] = pd.to_datetime(m.date_of_registration, errors="coerce")
m["addr_key"] = (m[addr_col].fillna("").astype(str).str.lower()
                   .str.replace(r"[^a-z0-9 ]", " ", regex=True)
                   .str.replace(r"\s+", " ", regex=True).str.strip())

per_addr = m.groupby("addr_key").cluster_id.nunique()
m["addr_clusters"] = m.addr_key.map(per_addr)
zero_pin = pd.to_numeric(m.pincode, errors="coerce").fillna(0) == 0
m["placeholder"] = ((m.addr_clusters >= MIN_ADDR_CLUSTERS) | zero_pin
                    | m.addr_key.str.startswith("na ") | (m.addr_key == ""))
m["virtual_kw"] = m.addr_key.str.contains(VIRTUAL, regex=True)

rows = []
for cid, g in m.groupby("cluster_id"):
    items = list(g[["entity_id", "company_name_normalized", "date"]].itertuples(index=False))
    for a, b in combinations(items, 2):
        if pd.isna(a.date) or pd.isna(b.date) or abs((a.date - b.date).days) > DATE_DAYS:
            continue
        na, nb = str(a.company_name_normalized), str(b.company_name_normalized)
        r = 1.0 if na == nb else SequenceMatcher(None, na, nb).ratio()
        if r >= NAME_RATIO:
            rows.append({"cluster_id": cid, "entity_a": a.entity_id, "entity_b": b.entity_id, "name_ratio": round(r, 3)})
dups = pd.DataFrame(rows, columns=["cluster_id", "entity_a", "entity_b", "name_ratio"])
dups.to_csv(OUT / "dup_pairs.csv", index=False)

g = m.groupby("cluster_id").agg(has_placeholder=("placeholder", "any"), virtual_share=("virtual_kw", "mean"),
                                max_addr_clusters=("addr_clusters", "max")).reset_index()
dq = sc.merge(g, on="cluster_id", how="left")
dq["n_dup_pairs"] = dq.cluster_id.map(dups.groupby("cluster_id").size()).fillna(0).astype(int)
dq["has_duplicate"] = dq.n_dup_pairs > 0
dq["artifact"] = dq.has_duplicate | dq.has_placeholder
dq.to_csv(OUT / "cluster_dq.csv", index=False)

# Look at these by hand before trusting the placeholder rule (keep local, in .gitignore)
per_addr.sort_values(ascending=False).head(50).rename("clusters").reset_index().to_csv(
    OUT / "placeholder_top50.csv", index=False)

out = dq.groupby("flag_category").agg(clusters=("cluster_id", "size"), duplicate=("has_duplicate", "sum"),
                                      placeholder=("has_placeholder", "sum"), artifact=("artifact", "sum"))
out["artifact_pct"] = (100 * out.artifact / out.clusters).round(1)
print(out)
