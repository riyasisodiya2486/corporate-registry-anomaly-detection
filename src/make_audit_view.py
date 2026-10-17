import pandas as pd

a = pd.read_csv("results/audit_sample.csv")
ent = pd.read_csv("results/snapshot/cleaned_entities.csv",
                  usecols=["entity_id", "company_name_raw", "address_raw",
                           "company_status", "authorized_capital", "date_of_registration"])
asg = pd.read_csv("results/snapshot/cluster_assignments.csv")

order = a.sample(frac=1, random_state=7)["cluster_id"].tolist()  # shuffled, blind to flag
lines = []
for cid in order:
    m = asg[asg.cluster_id == cid].merge(ent, on="entity_id")
    lines.append(f"\n=== CLUSTER {cid} ({len(m)} companies) ===")
    for _, r in m.iterrows():
        lines.append(f"- {r.company_name_raw} | {r.company_status} | cap {r.authorized_capital} "
                     f"| reg {r.date_of_registration}\n    {r.address_raw}")
open("results/audit_view.txt", "w", encoding="utf-8").write("\n".join(lines))
print("Wrote results/audit_view.txt for", len(order), "clusters")