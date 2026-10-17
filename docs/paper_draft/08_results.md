# Results (results-v1)

Status: figures and numbers final for git tag `results-v1`.

All numbers in this file come from the run frozen at git tag `results-v1`
(snapshot files in `results/snapshot/`). The live app is a demo and can lag
by up to 10 minutes because of caching; the snapshot is the source of record.

## Pipeline Output

- Companies analysed: 188,042 (MCA Company Master Data, ROC Pune)
- Candidate pairs generated: 4,269,766
- Matches (Jaro-Winkler): 46,298 (1.08% of candidate pairs)
- Graph: 19,972 nodes, 46,298 edges; 7,329 connected components
- Oversized components split with Louvain: 1; singletons dropped: 162
- Clusters: 7,384, covering 19,810 entities (largest cluster: 134 companies)
- Bridge clusters: 3,414 (46.2%)

## Anomaly Scoring and Flags

Isolation Forest (n_estimators=200, random_state=42) on six structural signals
plus the bridge flag. The status signal is excluded from the model and used
only for a separate weak-signal check.

- Thresholds (percentile cuts on the composite score): High Priority >= 74.26 (top 5%), Moderate >= 56.89 (next 15%)
- Flag distribution: High Priority 370 | Moderate 1,107 | Baseline 5,907
- Highest score: clusters 806 and 1585 tie at 100.00
- Weak-signal check: mean status_signal_score is 3.04 in high-priority clusters vs 2.61 overall (directional only, not validation)

The flag counts are fixed by the percentile rule, so they do not by themselves
show reproducibility. The score fingerprint below does.

## Explainability (SHAP)

SHAP values come from TreeExplainer on the saved Isolation Forest model.
A sign check (correlation -0.999 with our score convention) showed SHAP's
output is inverted relative to our convention, so values are negated before use.
SHAP explains the model's score, not whether a group is plausible: it shows which
signals drove the score. The database stores only the top 3 factors per cluster,
so any figure built from it counts top factors; it is not a mean SHAP over all signals.

## Reproducibility

Three unfixed runs gave different thresholds (71.94, 74.26 and 74.17) although
the inputs were identical. The cause was a missing ORDER BY on the table read:
Isolation Forest samples rows by position, so a different row order gave
different trees even with random_state=42. After adding ORDER BY cluster_id,
two standalone runs and one full-pipeline run produced the same score
fingerprint (MD5 of the composite scores rounded to 6 decimals):

`526924c4d0ef68107d447f085a73a90e`

with identical thresholds and an identical top-10 table. SHAP loads the saved
model (`models/iforest.joblib`), so scores and explanations come from one model.
The run_features.py import change made after the final run affects imports only,
not any calculation. Code and data are frozen at git tag `results-v1`.

## Full Pipeline Runtime

| Pipeline Stage | Execution Time | Status |
| :--- | :--- | :--- |
| Matching | 162.2s | PASS |
| Clustering | 11.8s | PASS |
| Feature Extraction | 181.0s | PASS |
| Isolation Forest | 7.4s | PASS |
| SHAP Explanations | 27.8s | PASS |
| Total | 390.2s | PASS |

Run on a laptop against Neon Postgres. An earlier full run gave 437.7s total;
the difference is normal timing variation.

## Case Study: Cluster 804

- 4 companies, composite score 60.99, classification Moderate
- Registered at the same address written four slightly different ways (same street, village and pincode 445302; they differ only in comma placement and the position of "India")
- Top factors: registered around the same time (1.0082), same type of business (0.7402), very similar company names (0.5925)

## Audit Plausibility Review (results-v1)

Sample: 20 high-priority and 20 baseline clusters drawn with random_state=42
from the final run (results/audit_sample.csv). Rule: docs/paper_draft/audit_rule.md,
written before review and amended during review (see its Amendments section).
Members were shown with scores and flags hidden, in shuffled order.

Result: 7 of 20 high-priority clusters were judged plausible (35%, 95% interval
about 18-57%). 5 of 20 baseline clusters were judged possible misses (25%,
interval about 11-47%). The intervals overlap, so this sample does not show that
the ranking clearly separates interesting from ordinary groups.

Seven of the 13 high-priority clusters judged not plausible were data artifacts:
the same company recorded twice, or a placeholder address (for example
"430 MANGAL, PUNE"). The other six were ordinary groups. Excluding artifacts,
7 of 13 were plausible; this is a post-hoc figure.

Limits: first-pass judgements were AI-assisted, confirmed by Riya and endorsed
by Yashika (not an independent blind check). There is no ground truth. The rule
uses features the model also measures, so the audit is partly circular. Results
are plausibility judgements, not precision.

An earlier audit on an older run (docs/manual_audit_day7.md) noted cluster 443
(score 44.16, Baseline): five cross-industry entities sharing a generic rural
post office address, which suggests the address signal under-weights shared
postal landmarks. It is not part of this sample.

## Limitations

- Small audit sample, no ground truth, no independent second rating
- Flags are statistical leads for human review, not findings of wrongdoing
- Duplicate registry records and placeholder addresses inflate flags; there is no deduplication stage
- Registry data has no director, shareholder or financial fields; director (DIN) links are the main extension
- Plausibility in the audit does not mean wrongdoing; "shell company" cannot be established from registry data
- 46.2% of clusters are flagged as bridges, so that signal separates little
- Status signal excluded from the model because it is weak
- Single registry office (ROC Pune); results may not generalise
- The database stores only the top 3 SHAP factors per cluster
- The deployed app is a public demo showing real company names; it uses a read-only database role (app_reader) and carries a visible "leads, not findings" notice