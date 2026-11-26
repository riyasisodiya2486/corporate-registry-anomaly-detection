"""Owner script, V2 only. Samples placeholder-flagged clusters for hand labelling. UNTESTED.
Needs results/v2/cluster_dq.csv (local, untracked).
Usage: python src/v2/placeholder_sample.py"""
import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")
dq = pd.read_csv("results/v2/cluster_dq.csv")
print("cluster_dq columns:", list(dq.columns))
need = {"cluster_id", "has_placeholder", "max_addr_clusters"}
if not need <= set(dq.columns):
    raise SystemExit("Expected columns missing. Send me the column list above.")
fl = dq[dq.has_placeholder.astype(bool)]
shared = fl[fl.max_addr_clusters >= 3]
other = fl[fl.max_addr_clusters < 3]
print("placeholder-flagged:", len(fl), "| address in 3+ clusters:", len(shared), "| other rules:", len(other))
pick = pd.concat([
    shared.sample(min(30, len(shared)), random_state=7).assign(rule="address in 3+ clusters"),
    other.sample(min(30, len(other)), random_state=7).assign(rule="pincode zero / blank / na"),
])
eng = create_engine(url)
rows = []
with eng.connect() as c:
    for cid, rule in zip(pick.cluster_id, pick.rule):
        m = pd.read_sql(
            text("SELECT e.company_name_raw, e.address_raw FROM cleaned_entities e JOIN cluster_assignments ca USING (entity_id) WHERE ca.cluster_id=:c ORDER BY e.entity_id LIMIT 3"),
            c,
            params={"c": int(cid)},
        )
        rows.append({
            "cluster_id": int(cid),
            "rule": rule,
            "sample_members": " || ".join(m.company_name_raw.fillna("") + " @ " + m.address_raw.fillna("")),
            "true_placeholder_or_shared_building": "",
        })
pd.DataFrame(rows).to_csv("results/v2/placeholder_sample.csv", index=False)
print("wrote results/v2/placeholder_sample.csv: label the last column yes/no")