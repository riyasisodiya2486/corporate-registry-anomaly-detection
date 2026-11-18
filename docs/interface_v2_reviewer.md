# v2 reviewer interface contract (Riya and Yashika agree, then freeze)

Status: PROPOSED by Riya. Yashika: comment or change by replying; freeze after both agree. Changes after freeze need both.

## Tables (sql/v2_reviewer_schema.sql, run by Yashika as owner on the v2 Neon branch)
- review_queue(cluster_id, batch)                 PK (cluster_id, batch); batch = 'r1', 'r2'
- reviewer_reviews(review_id, cluster_id, reviewer, review_mode, verdict, duplicate_record, address_type,
                   registered_close, directors_shared, filings_ok, office_exists, note, run_tag,
                   review_round, chain_hash, created_at)
  - review_mode: 'blind_queue' (counts as a label) | 'open' (stored, never used for evaluation)
  - verdict: worth_review | ordinary | data_artifact | need_more_info
  - Check answers (duplicate_record, address_type, registered_close, directors_shared, filings_ok, office_exists)
    are optional evidence; 'unknown' is allowed. directors_shared stays in the form but v2 has no director data.

## Roles
- app_reader   : SELECT on the 4 result tables only (unchanged). NO access to the two new tables.
- app_reviewer : SELECT on the 4 result tables + review_queue; SELECT, INSERT on reviewer_reviews; sequence usage.
- owner        : everything (used only by local scripts and by Yashika's chain script).

## Save flow (app/queries.py, already specified)
save_review(cluster_id, reviewer, mode, verdict, answers, note, run_tag) -> one INSERT, no updates, no deletes.
The app never writes scores, never writes audit_log.

## Chain flow (Yashika: src/v2/chain_reviews.py, owner connection)
For each reviewer_reviews row with chain_hash IS NULL, in review_id order:
  h = log_audit_action(conn, 'review:<mode>:<verdict>', cluster_id, reviewer); UPDATE chain_hash = h.
Run after each review session. Verification: the existing chain-verify function over audit_log.

## Label export (Riya: src/v2/export_reviews.py)
Blind-queue rows only; latest answer per (cluster, reviewer); Y = worth_review, N = ordinary, D = data_artifact;
need_more_info excluded; majority vote; ties go to results/v2/adjudication.csv; output results/v2/labels_final.csv.

## Rules
- Reviews never change scores automatically. Raters do not see score, flag or explanations in blind mode.
- Raters finish their own queue before any discussion. Test clusters (round 2 pool) are never used for training.
- Director-list data is excluded from v2 (OCR unreliable). directors_shared stays an optional manual answer.
