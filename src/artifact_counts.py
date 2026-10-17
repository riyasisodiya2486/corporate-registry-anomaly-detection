from pathlib import Path
import pandas as pd

S = Path("results/snapshot/")
e = pd.read_csv(
    S / "cleaned_entities.csv",
    usecols=[
        "entity_id",
        "company_name_normalized",
        "address_raw",
        "date_of_registration",
    ],
)
a = pd.read_csv(S / "cluster_assignments.csv")
sc = pd.read_csv(S / "cluster_scores.csv")

m = a.merge(e, on="entity_id")
m["addr"] = (
    m.address_raw.str.lower()
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)
m["date"] = pd.to_datetime(m.date_of_registration, errors="coerce")

# Placeholder heuristic: same address string in 3+ different clusters
per_addr = m.groupby("addr").cluster_id.nunique()
ph_addr = set(per_addr[per_addr >= 3].index)
ph_clusters = set(m[m.addr.isin(ph_addr)].cluster_id)

# Duplicate rule: same normalized name, registration dates within 3 days
g = (
    m.groupby(["cluster_id", "company_name_normalized"])
    .agg(n=("date", "size"), lo=("date", "min"), hi=("date", "max"))
    .reset_index()
)
g["dup"] = (g.n >= 2) & ((g.hi - g.lo).dt.days <= 3)
dup_clusters = set(g[g.dup].cluster_id)

sc["duplicate"] = sc.cluster_id.isin(dup_clusters)
sc["placeholder"] = sc.cluster_id.isin(ph_clusters)
sc["either"] = sc.duplicate | sc.placeholder

out = sc.groupby("flag_category").agg(
    clusters=("cluster_id", "size"),
    duplicate=("duplicate", "sum"),
    placeholder=("placeholder", "sum"),
    either=("either", "sum"),
)
out["either_pct"] = (100 * out.either / out.clusters).round(1)

print(out)
out.to_csv("results/artifact_counts.csv")