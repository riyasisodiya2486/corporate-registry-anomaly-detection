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
- Reclustering is frozen: the 7,384 clusters from v1 remain fixed.# Amendment to v2_plan.md (append, dated; do not edit the original text)

## Scope decision
The MCA disqualified-directors list is excluded from v2 because OCR validation was unreliable. It is future work.
The outside outcome check uses struck-off status only (status is never a model feature).

## Contributions to test
1. Artifact-aware scoring: duplicate and placeholder-address filter, checked on 100 hand-labelled pairs.
2. Blind structured review workflow with Cohen's kappa and hash-chained reviews.
3. Label-efficient ranking judged by reviewer effort: hit rate at 20 and reviews per worthwhile cluster.
4. Outside outcome check against struck-off status, reported by cluster size.

## Evaluation design (pooled blind review)
- Round 1: about 70 clusters (the 40 audited plus 30 new), reviewed blind. Used to train the supervised model.
- Round 2: top 20 of each system (v1, v1 with artifact filter, fixed-weight rule, logistic regression), excluding
  Round 1 clusters, plus 20 random clusters, shuffled and reviewed blind. Hit rate at 20 per system, bootstrap intervals.
- Clusters outside the pool stay unlabelled (known limit of pooling).

## Fixed success tests (set before building)
a. Artifact share among high-priority clusters under 5%.
b. v2 hit rate at 20 above v1, with intervals reported; overlap means "not established".
c. Cohen's kappa between raters at least 0.4 (otherwise revise the rubric and say so).
d. Two reruns give the same score fingerprint.
e. A failed test is reported as a failed test.

## Fixed rules
- The rule-score weights are fixed in model_compare.py and are not tuned on labels.
- The same 7,384 clusters are used (no reclustering in v2).
- No feature uses company_status. No director names are shown or published.
- AI-assisted judgements are never counted as independent labels.
