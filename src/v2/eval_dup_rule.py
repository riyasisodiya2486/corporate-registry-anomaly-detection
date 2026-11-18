"""Yashika or Riya. After labelling results/v2/pairs_to_label.csv (label = y or n)."""
import pandas as pd

lab = pd.read_csv("results/v2/pairs_to_label.csv")[["pair_id", "label"]]
flag = pd.read_csv("results/v2/pairs_rule_flag.csv")
d = lab.merge(flag, on="pair_id")
d["y"] = d.label.astype(str).str.lower().str.startswith("y")
f, nf = d[d.rule_flag], d[~d.rule_flag]
print("rule-flagged pairs:", len(f), "| truly duplicate:", int(f.y.sum()), "| precision:", round(f.y.mean(), 2))
print("not flagged (similar name, within 30 days):", len(nf), "| truly duplicate:", int(nf.y.sum()),
      "| miss rate in this pool:", round(nf.y.mean(), 2))
print("Note: the not-flagged pool is a sample of near misses, so this is a rough recall check only.")
