# v2 kit: what each file is, who runs it, in what order

Copy the folders into the repo root (src/v2, sql, app files, docs). Run every command from the project root with the venv active.

| Step | Owner   | File / command |
|------|---------|----------------|
| 1    | Riya    | git checkout v2-dev; git push -u origin v2-dev |
| 2    | both    | docs/interface_v2_reviewer.md (agree, freeze); append docs/v2_plan_amendment.md to docs/paper_draft/v2_plan.md |
| 3    | Yashika | Neon v2 branch; run sql/v2_reviewer_schema.sql; send the privilege check output |
| 4    | Riya    | python src/v2/weak_label_check.py |
| 5    | Yashika | python src/v2/data_quality.py ; look at results/v2/placeholder_top50.csv |
| 6    | Riya    | python src/v2/make_label_set.py ; python src/v2/load_review_queue.py results/v2/label_set_r1.csv r1 |
| 7    | Riya    | reviewer section code in app/main.py + app/queries.py (earlier guide, Steps 5 and 6); set QUEUE_BATCH = "r1" |
| 8    | Yashika | Streamlit secrets REVIEWER_DATABASE_URL and REVIEWER_PASSCODE; restrict viewers to named emails |
| 9    | all     | Round 1 blind reviews (Riya, Yashika, one classmate each side). No discussion until finished |
| 10   | Yashika | python src/v2/make_dup_pair_sample.py ; label results/v2/pairs_to_label.csv (y/n) ; python src/v2/eval_dup_rule.py |
| 11   | Yashika | python src/v2/chain_reviews.py (after fixing the import path) |
| 12   | Riya    | python src/v2/export_reviews.py ; write results/v2/adjudication.csv for ties ; re-run export |
| 13   | Riya    | python src/v2/build_v2_features.py ; python src/v2/model_compare.py |
| 14   | Riya    | python src/v2/pool_round2.py ; load_review_queue.py results/v2/label_set_r2.csv r2 ; set QUEUE_BATCH = "r2" |
| 15   | all     | Round 2 blind reviews |
| 16   | Riya    | python src/v2/export_reviews.py ; python src/v2/evaluate_pool.py |
| 17   | Riya    | app/v2_views.py + app/queries_v2_addition.py + app/main_patch_v2_views.md (network view, dossier) |
| 18   | Yashika | fill in src/v2/scaling_timing.py ; python src/v2/scaling_timing.py |
| 19   | Riya    | full v2 pipeline run on the Neon branch, fingerprint twice, snapshot, tag results-v2 |

.gitignore additions: results/review/  results/v2/pairs_to_label.csv  results/v2/pairs_rule_flag.csv
results/v2/placeholder_top50.csv  results/v2/pool_membership.csv  results/v2/dup_pairs.csv  .env
Never commit: raw reviews, pair files with company names, the director PDF, or any file with personal data.

Tested only on synthetic data (syntax and logic). Not run against your real database or snapshot.
