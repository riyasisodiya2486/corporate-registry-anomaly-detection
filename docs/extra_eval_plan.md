# Extra evaluation plan (fixed before running)

Date written: [insert date]. Written before any extra-evaluation result was seen.

## Outcome
A cluster has the outcome if at least one member company has status "Strike Off" or
"Under process of striking off". Company status is never a model feature. Struck-off
status is a loose proxy: companies are often struck off for non-filing, which is not
necessarily shell behaviour.

## Data
The existing 7,384 clusters and the stored cluster signals (V2 database, cluster_scores).
No reclustering. No new data.

## Systems compared
1. Stored composite score
2. Isolation Forest refit on all signals (random_state=42, otherwise default settings)
3. Isolation Forest refit with each single signal removed, one at a time
4. Fixed-weight rule: equal-weight mean of min-max scaled signals (no tuning)
5. Local Outlier Factor (n_neighbors=35, fixed, no tuning)
6. Cluster size only
7. Logistic regression, 5-fold out-of-fold predictions (supervised reference; uses the outcome
   as its training label, so it is a reference ceiling and not a fair competitor)
8. Random ranking (expected precision equals the base rate)

## Metrics
- AUC, with a bootstrap 95% interval
- Precision at K = 50, 100 and 370, with Wilson 95% intervals
- Enrichment lift: precision at K divided by the base rate of the outcome
- The stored score for size-2 clusters and size-3+ clusters separately
- The stored score with artifact clusters removed (frozen artifact definition,
  docs/artifact_definition.md)

## Rules
- No setting, signal, weight or threshold is changed after results are seen.
- Every system is reported, including those that do worse than the stored score.
- The refit Isolation Forest is the reference for the signal-removal rows, because its
  settings may differ from the original model.
- If the stored-score AUC differs materially from the earlier 0.589, the run is stopped and
  compared with weak_label_check.py before anything is reported.

## Not included (would need reclustering or new models; future work)
Synthetic anomaly injection, autoencoder, TF-IDF similarity, removal of Louvain splitting.

## Interpretation
Results are indications, not validation. Intervals are wide for small K. No claim is made
that any system detects wrongdoing or that it beats supervised systems.