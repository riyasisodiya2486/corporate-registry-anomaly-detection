import pandas as pd
audit = pd.read_csv("results/audit_sample_enriched.csv")

flagged = audit[audit["audit_group"] == "top_flagged"]
precision = (flagged["human_verdict"] == "plausible").mean()
print(f"Precision on top-20 flagged clusters: {precision:.1%} (n={len(flagged)})")

baseline = audit[audit["audit_group"] == "baseline_sample"]
false_negatives = (baseline["human_verdict"] == "plausible").sum()
print(f"Baseline clusters that look suspicious despite not being flagged: {false_negatives} / {len(baseline)}")

agreement = (flagged["shap_agrees_with_human"] == "yes").mean()
print(f"SHAP top-reason agreement with human judgment: {agreement:.1%}")