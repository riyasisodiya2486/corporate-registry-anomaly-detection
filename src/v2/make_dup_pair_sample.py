"""Yashika. 100 within-cluster pairs for hand-labelling 'same company recorded twice?' (y/n).
Output has company names: keep local, in .gitignore. The rule flag is stored separately so raters cannot see it."""
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

import pandas as pd

S = Path("results/snapshot")
OUT = Path("results/v2")
OUT.mkdir(parents=True, exist_ok=True)
ent = pd.read_csv(S / "cleaned_entities.csv",
                  usecols=["entity_id", "company_name_raw", "company_name_normalized", "address_raw", "date_of_registration"])
asg = pd.read_csv(S / "cluster_assignments.csv")[["entity_id", "cluster_id"]]
m = asg.merge(ent, on="entity_id")
m["date"] = pd.to_datetime(m.date_of_registration, errors="coerce")

rows = []
for cid, g in m.groupby("cluster_id"):
    items = list(g.itertuples(index=False))
    for a, b in combinations(items, 2):
        if pd.isna(a.date) or pd.isna(b.date) or abs((a.date - b.date).days) > 30:
            continue
        na, nb = str(a.company_name_normalized), str(b.company_name_normalized)
        r = 1.0 if na == nb else SequenceMatcher(None, na, nb).ratio()
        if r < 0.7:
            continue
        rows.append({"cluster_id": cid, "entity_a": a.entity_id, "entity_b": b.entity_id,
                     "name_a": a.company_name_raw, "name_b": b.company_name_raw,
                     "addr_a": a.address_raw, "addr_b": b.address_raw,
                     "date_a": a.date.date(), "date_b": b.date.date(),
                     "rule_flag": bool(r >= 0.92 and abs((a.date - b.date).days) <= 3)})
p = pd.DataFrame(rows)
flagged = p[p.rule_flag].sample(min(50, int(p.rule_flag.sum())), random_state=1)
other = p[~p.rule_flag].sample(min(50, int((~p.rule_flag).sum())), random_state=1)
s = pd.concat([flagged, other]).sample(frac=1, random_state=2).reset_index(drop=True)
s.insert(0, "pair_id", range(1, len(s) + 1))
s[["pair_id", "rule_flag"]].to_csv(OUT / "pairs_rule_flag.csv", index=False)
out = s.drop(columns=["rule_flag"]).copy()
out["label"] = ""            # fill with y or n
out.to_csv(OUT / "pairs_to_label.csv", index=False)
print(len(out), "pairs written; flagged:", int(s.rule_flag.sum()))
