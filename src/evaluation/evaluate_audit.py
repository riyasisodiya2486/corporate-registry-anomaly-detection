import pandas as pd

audit = pd.read_csv("results/audit_sample_enriched.csv")

flagged = audit[audit["audit_group"] == "top_flagged"]
precision = (flagged["human_verdict"] == "plausible").mean()
print(f"Precision on top-20 flagged clusters: {precision:.1%} (n={len(flagged)})")

baseline = audit[audit["audit_group"] == "baseline_sample"]
# FIX: baseline uses different vocabulary ("appropriately boring") than flagged rows ("plausible") —
# checking for "plausible" here could never match anything, regardless of the data.
suspicious_baseline = baseline[~baseline["human_verdict"].isin(["appropriately boring", ""])]
print(f"Baseline clusters that look suspicious despite not being flagged: {len(suspicious_baseline)} / {len(baseline)}")
if len(suspicious_baseline) > 0:
    print(suspicious_baseline[["cluster_id", "composite_score", "notes"]].to_string(index=False))

# FIX: case sensitivity — your actual data says "Yes"/"No", the old check only matched lowercase "yes"
agreement = (flagged["shap_agrees_with_human"].str.lower() == "yes").mean()
print(f"SHAP top-reason agreement with human judgment: {agreement:.1%}")