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


## Audit Precision
- Precision on top-20 flagged: 90.0% (n=20), after fixing a case-sensitivity bug and a vocabulary-mismatch bug in evaluate_audit.py
- 1/20 baseline false negative: Cluster 443, cross-industry entities sharing a rural address
- SHAP-human agreement: 90.0% — note: perfectly correlated with plausibility verdict, may not be independent, phrase carefully when writing prose later


## Reproducibility 
