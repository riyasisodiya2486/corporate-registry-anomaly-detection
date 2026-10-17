import pandas as pd

sc = pd.read_csv("results/snapshot/cluster_scores.csv")
ex = pd.read_csv("results/snapshot/cluster_explanations.csv")
top = (ex[ex["rank"] <= 3].sort_values(["cluster_id", "rank"])
         .groupby("cluster_id")["feature_name"].apply(", ".join).rename("top_factors"))

hi = sc[sc.flag_category == "high_priority"].sample(20, random_state=42)
lo = sc[sc.flag_category == "baseline"].sample(20, random_state=42)

out = (pd.concat([hi, lo])[["cluster_id", "cluster_size", "composite_score", "flag_category"]]
         .merge(top, on="cluster_id", how="left"))
out["judgement"] = ""
out["reason"] = ""
out.to_csv("results/audit_sample.csv", index=False)
print(out.to_string(index=False))