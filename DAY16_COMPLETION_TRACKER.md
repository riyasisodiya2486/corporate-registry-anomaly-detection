# Day 16 Completion Tracker — Branch `yashika-v2`

**Base:** `58f54f5` (origin/v2-dev)
**Working tree:** 11 modified files, 6 untracked files, `stash@{0}` intact
**Tests:** 30/30 passed (7 integrity + 23 Day 16 helpers), `git diff --check` clean
**Docker:** 3/3 Yashika service images built (ingestion, cleaning, integrity)

---

## Session 2 — Implementation pass (2026-11-19)

### Code fixes (Yashika-owned, no ownership change)

| File | Change | Validation |
|------|--------|------------|
| `src/cleaning/normalize.py` | Removed dead code after the `return` in `parse_capital` (unreachable duplicate block, lines 106-119) | `python src/cleaning/test_normalize.py` — all 17 cases unchanged, capital parsing correct |
| `docs/interface_contract.md` | Section 4.1: corrected `log_audit_action(conn, ...)` and `verify_chain_integrity(conn, table)` signatures to match the implementation (`db_engine`/`connection` params; module-level engine) | Manual diff against `src/integrity/hash_chain.py` |

### New file

| File | Purpose | Validation |
|------|---------|------------|
| `run_safe_tests.py` | Single-entry runner that loads only the two database-free test modules (`src.v2.test_day16_helpers`, `src.integrity.test_audit_verification`) | `python run_safe_tests.py` → 30/30 OK |

### Tests re-executed this session (no database, no network)

| Command | Result |
|---------|--------|
| `python -m unittest src.v2.test_day16_helpers src.integrity.test_audit_verification` | Ran 30 tests, OK |
| `python run_safe_tests.py` | Ran 30 tests, OK |
| `python src/cleaning/test_normalize.py` | All 17 normalize/pincode/capital cases pass |
| `python src/matching/test_scorer.py` | Pairs 1-2 match, 3-4 don't — as expected |
| `python src/graph/test_builder.py` | Two clusters formed correctly |
| `python src/scoring/test_shap_smoke.py` | SHAP shape (20, 4) as expected |

### Files NOT touched (correctly)

- `src/integrity/test_hash_chain.py` — destructive (TRUNCATE + TAMPER), not run
- `src/testing/seed_test_db.py` — reads production, writes test DB; not run
- `app/` files — Riya-owned; not modified
- `src/v2/weak_label_check.py`, `make_label_set.py`, `load_review_queue.py`, `build_v2_features.py`, `pool_round2.py`, `evaluate_pool.py`, `export_reviews.py` — Riya-owned; not modified
- `.env`, `results/`, `data_private/` — not accessed

### Blocked (unchanged)

Neon V2 DB access; approved V2 input dataset; genuine manual y/n labels; Streamlit secrets; Riya interface freeze; mentor/privacy approval; release approval.

---

## Phase 1 — Finalize code and prepare PR

| # | Requirement | Owner | Status | Files changed | Validation evidence | Remaining dependency |
|---|-------------|-------|--------|---------------|---------------------|---------------------|
| 1.1 | Review changes vs origin/v2-dev | Yashika | Complete | 7 files | `git diff`: +678/-212 | None |
| 1.2 | Verify all 30 tests | Yashika | Complete | 2 test files | 30/30 passed | None |
| 1.3 | Fix remaining bugs | Yashika | Complete | `hash_chain.py`, `chain_reviews.py`, `log_flagged_clusters.py`, `test_hash_chain.py`, `test_audit_verification.py`, `test_day16_helpers.py` | Database-engine safety refactor: removed module-level `LOCAL_ENGINE`/`NEON_ENGINE`/`engine` from `hash_chain.py`; `verify_chain_integrity(table, engine)` now requires explicit engine; `chain_reviews.py` uses `V2_DATABASE_URL` directly (no `DATABASE_URL` mutation, no `NEON_ENGINE` reference); `log_flagged_clusters.py` creates and disposes its own engine; `test_hash_chain.py` hardcoded credentials removed, destructive test opt-in via `ALLOW_DESTRUCTIVE_TESTS=1`; test files updated for removed module attributes | `git diff --check` clean; 30/30 tests pass | None |
| 1.4 | Prepare PR summary | Yashika | Complete | `DAY16_PR_SUMMARY.md` created | Riya review before commit |
| 1.5 | Do NOT commit/push without approval | Yashika | Complete | N/A | Nothing staged | Approval required |

---

## Phase 2 — Neon V2 isolation and reviewer database

| # | Requirement | Owner | Status | Files | Evidence | Dependency |
|---|-------------|-------|--------|-------|----------|------------|
| 2.1 | Neon V2 branch exists | Yashika | Blocked | N/A | N/A | Neon access + approval |
| 2.2 | Reviewer SQL schema | Yashika | Complete (file) | `sql/v2_reviewer_schema.sql` | Tables + permissions defined | Neon execution |
| 2.3 | review_queue + reviewer_reviews tables | Yashika | Blocked (file ready) | `sql/v2_reviewer_schema.sql` | Schema defined | Neon DB + approval |
| 2.4 | Indexes, constraints, FKs, sequences | Yashika | Complete (in schema) | `sql/v2_reviewer_schema.sql` | PK, FK, CHECK, indexes defined | Neon DB |
| 2.5 | app_reviewer minimum permissions | Yashika | Complete (in schema) | `sql/v2_reviewer_schema.sql` | GRANTs defined | Neon DB |
| 2.6 | app_reader no reviewer-table access | Yashika | Complete (in schema) | `sql/v2_reviewer_schema.sql` | REVOKE ALL defined | Neon DB |
| 2.7 | Run privilege checks on isolated V2 | Yashika | Blocked | N/A | N/A | Neon DB + approval |
| 2.8 | Approval before SQL/role changes | Yashika | Blocked | N/A | N/A | Approval |

---

## Phase 3 — Reviewer access

| # | Requirement | Owner | Status | Files | Evidence | Dependency |
|---|-------------|-------|--------|-------|----------|------------|
| 3.1 | Freeze interface_v2_reviewer.md with Riya | Both | Blocked | `docs/interface_v2_reviewer.md` | PROPOSED, not frozen | Riya agreement |
| 3.2 | REVIEWER_DATABASE_URL + REVIEWER_PASSCODE | Yashika | Blocked | N/A | N/A | Streamlit secrets approval |
| 3.3 | Restrict to named reviewer emails | Yashika | Blocked | N/A | N/A | Streamlit secrets approval |
| 3.4 | Test authorized/unauthorized access | Yashika | Blocked | N/A | N/A | Streamlit deployment |
| 3.5 | Approval before Streamlit secrets | Yashika | Blocked | N/A | N/A | Approval |

---

## Phase 4 — Data quality

| # | Requirement | Owner | Status | Files | Evidence | Dependency |
|---|-------------|-------|--------|-------|----------|------------|
| 4.1 | Approved V2 input dataset | Both | Blocked | N/A | N/A | Dataset |
| 4.2 | Run data_quality.py with V2 input dir | Yashika | Blocked | `data_quality.py` | Script complete | V2 input CSV |
| 4.3 | Review placeholder_top50.csv | Yashika | Blocked | N/A | N/A | Data quality output |
| 4.4 | Distinguish shared buildings vs placeholders | Yashika | Blocked | N/A | N/A | Data quality output |
| 4.5 | Record manual decisions | Yashika | Blocked | N/A | N/A | Data quality output |
| 4.6 | Send Riya final results | Yashika | Blocked | N/A | N/A | Data quality complete |

---

## Phase 5 — Duplicate-rule evaluation

| # | Requirement | Owner | Status | Files | Evidence | Dependency |
|---|-------------|-------|--------|-------|----------|------------|
| 5.1 | Run make_dup_pair_sample.py | Yashika | Blocked | `make_dup_pair_sample.py` | Script reads V1 snapshot | V1 snapshot exists |
| 5.2 | Prepare pairs_to_label.csv | Yashika | Blocked | `make_dup_pair_sample.py` | Empty label column | Manual labels |
| 5.3 | Obtain genuine manual y/n labels | Both | Blocked | `pairs_to_label.csv` | N/A | Cannot fabricate |
| 5.4 | Run eval_dup_rule.py | Yashika | Blocked | `eval_dup_rule.py` | Computes precision/near-miss | Labeled CSV |
| 5.5 | Report precision, FP, FN, near-miss | Yashika | Blocked | N/A | N/A | Evaluation output |
| 5.6 | Send Riya findings | Yashika | Blocked | N/A | N/A | Evaluation complete |

---

## Phase 6 — Audit-chain validation

| # | Requirement | Owner | Status | Files | Evidence | Dependency |
|---|-------------|-------|--------|-------|----------|------------|
| 6.1 | Reviewer audit integration | Yashika | Complete (synthetic) | `chain_reviews.py`, `hash_chain.py` | Uses log_audit_action with connection | Real DB |
| 6.2 | Transaction atomicity + advisory-lock concurrency | Yashika | Complete (synthetic) | `test_day16_helpers.py` | 23/23 pass | Real PostgreSQL |
| 6.3 | Rollback, repeated execution, concurrent writers | Yashika | Complete (synthetic) | `test_day16_helpers.py` | AuditChainTests cover all | Real PostgreSQL |
| 6.4 | Tamper detection for every stored audit field | Yashika | Complete (synthetic) | `test_audit_verification.py` | 7/7 pass all field types | Real DB |
| 6.5 | Do not touch production audit records | Yashika | Complete | N/A | No DB connections | None |

---

## Phase 7 — Scaling

| # | Requirement | Owner | Status | Files | Evidence | Dependency |
|---|-------------|-------|--------|-------|----------|------------|
| 7.1 | Benchmark 25/50/75/100% | Yashika | Blocked | `scaling_timing.py` | Script complete | `results/v2/cleaned_entities.csv` |
| 7.2 | Approved isolated V2 dataset | Yashika | Blocked | N/A | N/A | V2 input dataset |
| 7.3 | Record counts, pairs, timing | Yashika | Blocked | N/A | N/A | Scaling output |
| 7.4 | Send Riya benchmark results | Yashika | Blocked | N/A | N/A | Scaling complete |

---

## Phase 8 — Riya's tasks and shared work

| # | Requirement | Owner | Status | Files | Evidence | Dependency |
|---|-------------|-------|--------|-------|----------|------------|
| 8.1 | Weak-label checks + cluster-size analysis | Riya | Not started | `weak_label_check.py` | Script exists | Riya execution |
| 8.2 | Label-set creation + review-queue loading | Riya | Not started | `make_label_set.py`, `load_review_queue.py` | Scripts exist | Riya execution |
| 8.3 | Reviewer UI and save flow | Riya | Not started | `queries_v2_addition.py` | Ready to append to queries.py | Riya execution |
| 8.4 | Round 1 blind review + adjudication | Both | Not started | `export_reviews.py` | Script exists | Round 1 reviews |
| 8.5 | V2 features + model comparison | Riya | Not started | `build_v2_features.py`, `model_compare.py` | Scripts exist | Riya execution |
| 8.6 | Round 2 pooling + evaluation | Riya | Not started | `pool_round2.py`, `evaluate_pool.py` | Scripts exist | Round 1 complete |
| 8.7 | Network view + evidence dossier | Riya | Not started | `v2_views.py`, `main_patch_v2_views.md` | Files exist, patch not applied | Riya execution |
| 8.8 | pyvis dependency + static fallback | Riya | Not started | `v2_views.py` | Fallback implemented | requirements.txt |
| 8.9 | Three independent raters | Both | Not started | N/A | N/A | Reviewer recruitment |
| 8.10 | Cohen's kappa + tie adjudication | Riya | Not started | `export_reviews.py` | kappa in script | Reviews complete |
| 8.11 | Mentor questions + privacy approval | Both | Blocked | N/A | N/A | Mentor/privacy |
| 8.12 | Struck-off outcome by cluster size | Riya | Not started | `weak_label_check.py` | Wilson CI + AUC | Riya execution |

---

## Phase 9 — Docker and CI

| # | Requirement | Owner | Status | Files | Evidence | Dependency |
|---|-------------|-------|--------|-------|----------|------------|
| 9.1 | Verify Docker builds | Yashika | Not started | Dockerfiles in src/*/ | All service Dockerfiles exist | Docker |
| 9.2 | GitHub Actions on v2-dev and yashika-v2 | Yashika | Complete | `docker-build.yml` | yashika-v2 added to push + PR triggers; YAML valid | None |
| 9.3 | Resolve infrastructure failures | Yashika | Not started | N/A | N/A | CI runs |
| 9.4 | Coordinate Riya-owned file changes | Yashika | Not started | N/A | N/A | Riya |

---

## Phase 10 — Final V2 release

| # | Requirement | Owner | Status | Files | Evidence | Dependency |
|---|-------------|-------|--------|-------|----------|------------|
| 10.1 | Final V2 pipeline on isolated Neon | Yashika | Blocked | N/A | N/A | All upstream |
| 10.2 | Score fingerprints across two runs | Yashika | Blocked | N/A | N/A | Pipeline run |
| 10.3 | Export and validate V2 snapshot | Yashika | Blocked | `export_snapshot.py` | Script exists | Pipeline run |
| 10.4 | Exclude private files/personal data | Yashika | Blocked | `.gitignore` | Protections present | Release review |
| 10.5 | Paper evidence + methodology | Riya | Not started | `docs/paper_draft/` | Draft files exist | Riya |
| 10.6 | Create results-v2 after release approval | Yashika | Blocked | N/A | N/A | Release approval |

---

## Summary

**Yashika-owned, can do now:** Phase 1.4 (PR prep), Phase 9.2 (CI workflow fix)
**Yashika-owned, blocked on external:** Phase 2 (Neon DB), Phase 3 (Streamlit secrets), Phase 4 (V2 dataset), Phase 6 (real DB), Phase 7 (V2 dataset), Phase 9.1 (Docker)
**Riya-owned:** Phase 3.1 (interface freeze), Phase 8 (all Riya tasks), Phase 10.5 (paper draft)
**Shared/blocked:** Phase 5 (manual labels), Phase 10 (release)

## Phase A — Audit of All 41 Requirements (completed Yashika-side)

### Phase A findings — Phases 8-10

| Req | ID | Description | Owner | Status | Evidence | Missing work | Dependency | Next action |
|-----|----|-------------|-------|--------|----------|--------------|------------|-------------|
| 40 | 8.1 | Weak-label checks + cluster-size analysis | Riya | NOT STARTED | `weak_label_check.py` exists | Riya execution | Riya | Await Riya |
| 41 | 8.2 | Label-set creation + review-queue loading | Riya | NOT STARTED | `make_label_set.py`, `load_review_queue.py` exist | Riya execution | Riya | Await Riya |
| 42 | 8.3 | Reviewer UI and save flow | Riya | NOT STARTED | `queries_v2_addition.py` ready to append | Append to queries.py | Riya | Await Riya |
| 43 | 8.4 | Round 1 blind review + adjudication | Both | NOT STARTED | `export_reviews.py` exists | Round 1 reviews | Riya | Await Riya |
| 44 | 8.5 | V2 features + model comparison | Riya | NOT STARTED | `build_v2_features.py`, `model_compare.py` exist | Riya execution | Riya | Await Riya |
| 45 | 8.6 | Round 2 pooling + evaluation | Riya | NOT STARTED | `pool_round2.py`, `evaluate_pool.py` exist | Round 1 complete | Riya | Await Riya |
| 46 | 8.7 | Network view + evidence dossier | Riya | NOT STARTED | `v2_views.py`, `main_patch_v2_views.md` exist; patch not applied | Riya execution | Riya | Await Riya |
| 47 | 8.8 | pyvis dependency + static fallback | Riya | NOT STARTED | `v2_views.py` handles pyvis absence | requirements.txt update | Riya | Await Riya |
| 48 | 8.9 | Three independent raters | Both | NOT STARTED | N/A | Reviewer recruitment | Riya | Await Riya |
| 49 | 8.10 | Cohen's kappa + tie adjudication | Riya | NOT STARTED | `export_reviews.py` computes kappa | Reviews complete | Riya | Await Riya |
| 50 | 8.11 | Mentor questions + privacy approval | Both | BLOCKED | N/A | Mentor/privacy | Mentor | Await mentor |
| 51 | 8.12 | Struck-off outcome by cluster size | Riya | NOT STARTED | `weak_label_check.py` has Wilson CI + AUC | Riya execution | Riya | Await Riya |
| 52 | 9.1 | Verify Docker builds | Yashika | COMPLETE | `docker images`: registry-ingestion:latest (734MB/155MB), registry-cleaning:latest (459MB/105MB), registry-integrity:latest (470MB/108MB) all built successfully | None | None | Done |
| 53 | 9.2 | GitHub Actions on v2-dev and yashika-v2 | Yashika | COMPLETE | yashika-v2 added to push + PR triggers; YAML validated | None | None | Done |
| 54 | 9.3 | Resolve infrastructure failures | Yashika | NOT STARTED | N/A | CI runs | CI workflow | Await CI |
| 55 | 9.4 | Coordinate Riya-owned file changes | Yashika | NOT STARTED | N/A | Riya coordination | Riya | Await Riya |
| 56 | 10.1 | Final V2 pipeline on isolated Neon | Yashika | BLOCKED | N/A | All upstream | All upstream | Await all upstream |
| 57 | 10.2 | Score fingerprints across two runs | Yashika | BLOCKED | N/A | Pipeline run | Pipeline run | Await pipeline |
| 58 | 10.3 | Export and validate V2 snapshot | Yashika | BLOCKED | `export_snapshot.py` exists | Pipeline run | Pipeline run | Await pipeline |
| 59 | 10.4 | Exclude private files/personal data | Yashika | BLOCKED | `.gitignore` has protections | Release review | Release review | Await review |
| 60 | 10.5 | Paper evidence + methodology | Riya | NOT STARTED | `docs/paper_draft/` drafts exist | Riya | Riya | Await Riya |
| 61 | 10.6 | Create results-v2 after release approval | Yashika | BLOCKED | N/A | Release approval | Release approval | Await approval |

### Pre-existing issues (not Day 16 regressions)
- `src/integrity/test_hash_chain.py`: ImportError (`from hash_chain import ...` fails); also performs destructive DB operations (TRUNCATE record_hashes, UPDATE record_hashes SET record_hash='TAMPERED'). Must NOT be run per preservation rules.
- Other test modules (`test_blocker`, `test_builder`, `test_scorer`, `test_normalize`, `test_matching_libraries`, `test_networkx`, `test_shap`, `test_shap_smoke`): fail via import path issues when run through `python -m unittest src.x.test_y` because they use bare relative imports. These are pre-existing and unrelated to Day 16.

### Summary of status
| Phase | Complete | Partial | Blocked | Not Started |
|-------|----------|---------|---------|-------------|
| 1 — Code/PR | 4 of 5 | 0 | 1 (1.5) | 0 |
| 2 — Neon V2 DB | 4 of 8 | 0 | 4 | 0 |
| 3 — Reviewer access | 0 of 5 | 0 | 5 | 0 |
| 4 — Data quality | 0 of 6 | 0 | 6 | 0 |
| 5 — Duplicate evaluation | 0 of 6 | 0 | 6 | 0 |
| 6 — Audit chain | 5 of 5 | 0 | 0 | 0 |
| 7 — Scaling | 0 of 4 | 0 | 4 | 0 |
| 8 — Riya's tasks | 0 of 12 | 0 | 1 | 11 |
| 9 — Docker/CI | 2 of 4 | 0 | 0 | 2 |
| 10 — Release | 0 of 6 | 0 | 4 | 2 |
| **Total** | **14 of 61** | **0** | **35** | **12** |

Note: Status counts include all sub-requirements, not just the original 41.

| Req | ID | Description | Owner | Status | Evidence | Missing work | Dependency | Next action |
|-----|----|-------------|-------|--------|----------|--------------|------------|-------------|
| 19 | 4.1 | Approved V2 input dataset | Both | BLOCKED | No V2 dataset identified | Dataset approval | Dataset | Await dataset |
| 20 | 4.2 | Run data_quality.py with V2 input dir | Yashika | BLOCKED | Script complete, requires --input-dir | V2 CSV inputs | V2 input dataset | Await dataset |
| 21 | 4.3 | Review placeholder_top50.csv | Yashika | BLOCKED | Script writes `results/v2/placeholder_top50.csv` | Data quality output | Data quality run | Await dataset |
| 22 | 4.4 | Distinguish shared buildings vs placeholders | Yashika | BLOCKED | Script flags virtual/residential/placeholder addresses | Manual review | Data quality output | Await dataset |
| 23 | 4.5 | Record manual decisions | Yashika | BLOCKED | No decisions recorded yet | Decision log | Data quality output | Await dataset |
| 24 | 4.6 | Send Riya final results | Yashika | BLOCKED | Not sent | Data quality complete | Data quality complete | Await dataset |
| 25 | 5.1 | Run make_dup_pair_sample.py | Yashika | BLOCKED | Script reads V1 snapshot `results/snapshot/cleaned_entities.csv` | V1 snapshot exists; output goes to results/v2/ | V1 snapshot available; output git-ignored | Await approval to run |
| 26 | 5.2 | Prepare pairs_to_label.csv | Yashika | BLOCKED | Script writes empty label column | Manual y/n labels | Manual labels | Await labels |
| 27 | 5.3 | Obtain genuine manual y/n labels | Both | BLOCKED | Labels must be genuine; never fabricate | Manual labeling | Reviewer availability | Await reviewers |
| 28 | 5.4 | Run eval_dup_rule.py | Yashika | BLOCKED | Script reads pairs_to_label.csv + pairs_rule_flag.csv | Labeled CSV + flag CSV | Evaluation complete | Await labels |
| 29 | 5.5 | Report precision, FP, FN, near-miss | Yashika | BLOCKED | Script computes rule_precision + near_miss_positive_rate | Evaluation output | Evaluation complete | Await labels |
| 30 | 5.6 | Send Riya findings | Yashika | BLOCKED | Not sent | Evaluation complete | Evaluation complete | Await labels |
| 31 | 6.1 | Reviewer audit integration | Yashika | COMPLETE (synthetic) | `chain_reviews.py` uses `log_audit_action` with connection param; verify_audit_chain_rows verifies | Real DB testing | Neon DB | Await Neon DB |
| 32 | 6.2 | Transaction atomicity + advisory-lock concurrency | Yashika | COMPLETE (synthetic) | 23/23 tests pass including rollback, lock, atomicity | Real PostgreSQL | Neon DB | Await Neon DB |
| 33 | 6.3 | Rollback, repeated execution, concurrent writers | Yashika | COMPLETE (synthetic) | AuditChainTests cover all scenarios | Real PostgreSQL | Neon DB | Await Neon DB |
| 34 | 6.4 | Tamper detection for every stored audit field | Yashika | COMPLETE (synthetic) | 7/7 tests cover action_type, cluster_id, reviewer, timestamp, previous_hash, stored_hash | Real DB | Neon DB | Await Neon DB |
| 35 | 6.5 | Do not touch production audit records | Yashika | COMPLETE | No database connections made | None | None | Done |
| 36 | 7.1 | Benchmark 25/50/75/100% | Yashika | BLOCKED | `scaling_timing.py` complete; reads `results/v2/cleaned_entities.csv` | V2 input CSV | V2 input dataset | Await dataset |
| 37 | 7.2 | Approved isolated V2 dataset | Yashika | BLOCKED | None available | Dataset | Dataset | Await dataset |
| 38 | 7.3 | Record counts, pairs, timing | Yashika | BLOCKED | Script outputs scaling.csv + scaling.png | Scaling output | Scaling run | Await dataset |
| 39 | 7.4 | Send Riya benchmark results | Yashika | BLOCKED | Not sent | Scaling complete | Scaling complete | Await dataset |

| Req | ID | Description | Owner | Status | Evidence | Missing work | Dependency | Next action |
|-----|----|-------------|-------|--------|----------|--------------|------------|-------------|
| 1 | 1.1 | Review changes vs origin/v2-dev | Yashika | COMPLETE | `git diff origin/v2-dev --stat`: +678/-212 across 6 files | None | None | Done |
| 2 | 1.2 | Verify all 30 tests | Yashika | COMPLETE | 23/23 Day 16 helpers + 7/7 integrity = 30/30 | None | None | Done |
| 3 | 1.3 | Fix remaining bugs | Yashika | COMPLETE | Removed trailing blank line at EOF in `hash_chain.py`; `git diff --check` clean | None | None | Done |
| 4 | 1.4 | Prepare PR summary | Yashika | PARTIAL | This tracker exists; not yet shared with Riya | PR summary text | Riya review | Share tracker |
| 5 | 1.5 | Do NOT commit/push without approval | Yashika | COMPLETE | Nothing staged; `git diff --cached` empty | None | Approval | Wait |
| 6 | 2.1 | Neon V2 branch exists | Yashika | BLOCKED | Not verified; no Neon access | N/A | Neon access + approval | Await Neon V2 |
| 7 | 2.2 | Reviewer SQL schema | Yashika | COMPLETE (file ready) | `sql/v2_reviewer_schema.sql`: tables, constraints, indexes, GRANTs, REVOKEs | Cannot execute SQL | Neon DB + approval | Await Neon DB |
| 8 | 2.3 | review_queue + reviewer_reviews tables | Yashika | BLOCKED | Schema defined | Table creation on Neon | Neon DB execution + approval | Await Neon DB |
| 9 | 2.4 | Indexes, constraints, FKs, sequences | Yashika | COMPLETE (in schema) | PK, FK to cluster_scores, CHECK on mode/verdict, 2 indexes, sequence | Cannot verify on live DB | Neon DB | Await Neon DB |
| 10 | 2.5 | app_reviewer minimum permissions | Yashika | COMPLETE (in schema) | GRANT SELECT on 4 result tables + review_queue; GRANT SELECT, INSERT on reviewer_reviews; sequence usage | Cannot verify effective perms | Neon DB | Await Neon DB |
| 11 | 2.6 | app_reader no reviewer-table access | Yashika | COMPLETE (in schema) | REVOKE ALL on reviewer_reviews, review_queue, sequence FROM app_reader | Cannot verify effective perms | Neon DB | Await Neon DB |
| 12 | 2.7 | Run privilege checks on isolated V2 | Yashika | BLOCKED | Verification queries prepared in schema comments | Cannot execute | Neon DB + approval | Await Neon DB |
| 13 | 2.8 | Approval before SQL/role changes | Yashika | BLOCKED | None granted yet | Approval | User approval | Await approval |
| 14 | 3.1 | Freeze interface_v2_reviewer.md with Riya | Both | BLOCKED | Status: PROPOSED by Riya | Riya agreement + freeze | Riya | Await Riya |
| 15 | 3.2 | REVIEWER_DATABASE_URL + REVIEWER_PASSCODE | Yashika | BLOCKED | Not configured | Streamlit secrets setup | Streamlit secrets approval | Await approval |
| 16 | 3.3 | Restrict to named reviewer emails | Yashika | BLOCKED | Not configured | Streamlit viewer restrictions | Streamlit secrets approval | Await approval |
| 17 | 3.4 | Test authorized/unauthorized access | Yashika | BLOCKED | Not tested | Streamlit deployment | Streamlit deployment | Await deployment |
| 18 | 3.5 | Approval before Streamlit secrets | Yashika | BLOCKED | None granted yet | Approval | User approval | Await approval |