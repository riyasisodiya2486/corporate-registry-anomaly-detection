# V2 Artifact Definition (Frozen: 2026-11-21)

This definition is frozen prior to viewing Round 1 human labels and will not be modified after labels are observed.

## Rule Specification
A cluster is classified as an artifact if `has_duplicate OR has_placeholder`:

1. **Duplicate rule (`has_duplicate`):** Clusters containing near-duplicate entity records as defined in `src/v2/data_quality.py`.
2. **Placeholder rule (`has_placeholder`):** Clusters matching any of the following:
   - Shared address across 3 or more clusters (`addr_clusters >= 3`)
   - Numeric `pincode == 0`
   - Blank or `"na "` registered address

## Baseline V2 Counts (Measured on V2 Snapshot)
- **Duplicate clusters (`has_duplicate`):** 213
- **Placeholder clusters (`has_placeholder`):** 649 (of which **269** are flagged by `addr_clusters >= 3`, the broadest placeholder rule)
- **Total artifact clusters (`has_duplicate OR has_placeholder`):** 696 (28.4%% of high-priority clusters; v2 post-filter target is less than 5%%)

## Duplicate Rule Validation (`eval_dup_rule.py`, 100 Hand-Labelled Pairs)
- **Rule-flagged pairs (n = 50):** 15 truly duplicate — **Precision = 0.30 (30%%)**
- **Unflagged near-miss pairs (n = 50):** 1 truly duplicate — **Near-miss positive rate = 0.02 (2%%)** (from the sampled near-miss pool, not a dataset-wide miss-rate estimate)

## Comparison with V1
Earlier v1 artifact figures (3.5%% / 9.6%% / 19.5%%) used a narrower v1 rule set and are reported separately under their v1 definition without mixing v1 and v2 counts.
