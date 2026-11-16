# Version 2 Engineering and Evaluation Plan (v2-dev)

## Core Objectives
1. **Rigor & Verification:** Implement a blind human verification queue with inter-rater agreement tracking.
2. **Data Quality Layer:** Introduce explicit duplicate and placeholder/shared-building address rules.
3. **Supervised & Comparative Modeling:** Compare unsupervised baselines against proxy features and supervised models trained exclusively on blind-queue audit labels.
4. **Investigative Utility:** Deploy an interactive network view and evidence dossier in Streamlit using observation-only wording ("leads, not findings").

## Fixed Success Tests
a. **Precision at Top 20:** On the test split, v2 precision at $n=20$ exceeds v1 precision.
b. **Artifact Reduction:** High-priority cluster duplication/placeholder share drops below 5%.
c. **Reproducibility:** Multiple pipeline reruns yield an identical score fingerprint.
d. **Supervised Performance:** Report supervised PR-AUC openly against unsupervised baselines.

## Evaluation Rules
- The test split is touched exactly once.
- Blind queue labels are the sole ground truth for evaluation.
- Remarks never alter scores automatically.
- Reclustering is frozen: the 7,384 clusters from v1 remain fixed.