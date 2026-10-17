# Audit rule (written before reviewing, results-v1)

Sample: 20 high-priority and 20 baseline clusters, random_state=42,
from results/snapshot/cluster_scores.csv (file: results/audit_sample.csv).

Question asked of every cluster:
"Would a reviewer reasonably want to look at this group of companies more closely?"

Judgement = yes if at least one of these is visible in Cluster Detail:
1. Members share the same or near-identical address written differently.
2. Members have near-identical names or a repeating naming pattern.
3. Members were registered within a short time window (days or weeks).
4. Members share a combination of the above plus similar authorized capital.

Judgement = no if the similarity is plausibly ordinary, for example a
well-known co-working address, a shared building with unrelated businesses,
or a common word in the name (for example "Enterprises") with nothing else shared.

Rules for fairness:
- Decide from the Cluster Detail page only, in the order of the sample file.
- Write one short reason per row.
- Do not look at the score before judging if possible (hide that column).
- This is one reviewer's judgement, with no ground truth.
  Results are "plausibility", not "accuracy" or "true positives".
- Baseline rows: judgement = yes means a possible miss (false negative).
- Reviewer: Riya. If time allows, Yashika independently judges 10 rows
  and agreement is reported.