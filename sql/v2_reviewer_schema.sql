-- Run by Yashika, as neondb_owner, on the v2 Neon branch (never on production first).
CREATE TABLE IF NOT EXISTS review_queue (
  cluster_id INTEGER NOT NULL REFERENCES cluster_scores(cluster_id),
  batch      TEXT    NOT NULL,                 -- 'r1', 'r2', ...
  PRIMARY KEY (cluster_id, batch)
);

CREATE TABLE IF NOT EXISTS reviewer_reviews (
  review_id        SERIAL PRIMARY KEY,
  cluster_id       INTEGER NOT NULL REFERENCES cluster_scores(cluster_id),
  reviewer         TEXT    NOT NULL,
  review_mode      TEXT    NOT NULL CHECK (review_mode IN ('blind_queue','open')),
  verdict          TEXT    NOT NULL CHECK (verdict IN ('worth_review','ordinary','data_artifact','need_more_info')),
  duplicate_record TEXT,
  address_type     TEXT,
  registered_close TEXT,
  directors_shared TEXT,
  filings_ok       TEXT,
  office_exists    TEXT,
  note             TEXT,
  run_tag          TEXT    NOT NULL,
  review_round     TEXT    NOT NULL DEFAULT 'r1',
  chain_hash       TEXT,                        -- filled by the owner-side chain script only
  created_at       TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reviews_cluster ON reviewer_reviews(cluster_id);
CREATE INDEX IF NOT EXISTS idx_entities_addr ON cleaned_entities(address_normalized);

-- Reviewer login role: create it first on the Neon console Roles page if SQL refuses.
GRANT USAGE ON SCHEMA public TO app_reviewer;
GRANT SELECT ON cleaned_entities, cluster_assignments, cluster_scores, cluster_explanations, review_queue TO app_reviewer;
GRANT SELECT, INSERT ON reviewer_reviews TO app_reviewer;
GRANT USAGE, SELECT ON SEQUENCE reviewer_reviews_review_id_seq TO app_reviewer;

-- The Day 12 default-privileges rule gives app_reader SELECT on every new table. Remove it for these two.
REVOKE ALL ON reviewer_reviews, review_queue FROM app_reader;
REVOKE ALL ON SEQUENCE reviewer_reviews_review_id_seq FROM app_reader;

-- Check (app_reader must NOT appear for the two new tables):
-- SELECT grantee, table_name, privilege_type FROM information_schema.role_table_grants
--   WHERE table_name IN ('reviewer_reviews','review_queue') ORDER BY grantee, table_name;
