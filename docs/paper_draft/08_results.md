## Audit Precision & Human Validation

To evaluate model precision, explainability alignment, and edge-case behavior, we conducted an expanded manual audit across 40 clusters ($n=20$ top-flagged clusters vs. $n=20$ randomized baseline clusters).

### Precision Findings
The model achieved **90.0% precision** ($n=18/20$) on top-flagged clusters. True positive detections spanned three primary structural typologies:
1. **Shadow Nidhi Financial Networks** (e.g., Cluster 806): Cross-taluka entities sharing identical naming patterns and capital structures.
2. **Rapid SPV Shell Networks** (e.g., Cluster 1585): Multi-entity incorporations within tight 4-day time windows sharing care-of ("C/O") addresses.
3. **High Operational Churn Co-locations** (e.g., Cluster 629): Co-located entities exhibiting mixed corporate statuses (struck off vs. active).

The two false positives ($n=2/20$, Clusters 739 and 1714) stemmed from policy artifacts—specifically Farmer Producer Companies (FPCs) incorporated under state agricultural schemes sharing local administrative address nodes.

### Baseline False-Negative Analysis & Limitations
Evaluation of the baseline sample ($n=20$) confirmed that **95.0%** ($n=19/20$) of non-flagged clusters were appropriately categorized as standard commercial operations, family legacy entities, or routine LLP restructurings.

However, the audit identified **1 false negative** (Cluster 443, Composite Score: 44.16). Cluster 443 consists of 5 cross-industry entities (spanning Nidhi, Dairy, Farmer Producer, and Automations) sharing a generic rural post office address. This finding highlights a key model limitation: the address similarity signal can under-weight density anomalies in sparse rural administrative zones where distinct businesses rely on shared postal landmarks.

### SHAP-Human Agreement
The model's primary SHAP feature driver aligned with human analytical reasoning in **90.0%** ($n=18/20$) of top-flagged cases.

*Methodological Note:* We observe a 1:1 correspondence between human plausibility decisions and SHAP feature alignment across the audited sample. While SHAP attributions (e.g., prioritizing `topology_score` or `timing_signal_score`) consistently matched expert reasoning, this metric should be interpreted as directionally consistent with plausibility judgment rather than a fully independent evaluation dimension.


## Reproducibility

An independent execution of the pipeline from the entity-matching stage through anomaly scoring and explanation generation confirmed **100% deterministic reproducibility** across all outputs. Fixed pseudo-random seeds (`random_state=42` across Louvain community detection and Isolation Forest model training) ensured zero variance across runs.

Key metrics verified across independent executions:
- **Total Entities Evaluated:** 188,042
- **Pairwise Graph Edges / Matches:** 46,298
- **Identified Clusters:** 7,384 (Max cluster size: 134)
- **Anomaly Scoring Thresholds:** High Priority ($\ge 74.26$) | Moderate ($\ge 56.89$)
- **Risk Category Distribution:** High Priority: 370 | Moderate: 1,107 | Baseline: 5,907

A sign-verification check confirmed SHAP's native output was inversely oriented to our composite score convention ($r = -0.999$), corrected by negating `shap_values` before use — see Methodology, Explainability, for detail.


## Full Pipeline Runtime

*(Pending — awaiting a fresh, real terminal log of the Isolation Forest re-run with the batched-update fix applied. Using Day 9's confirmed figures below until then; do not estimate or transcribe from memory.)*

| Pipeline Stage | Execution Time | Status |
| :--- | :--- | :--- |
| Matching | 163.1s | PASS |
| Clustering | 22.9s | PASS |
| Feature Extraction | 227.2s | PASS |
| Isolation Forest | *pending re-run* | — |
| SHAP Explanations | 34.0s | PASS |