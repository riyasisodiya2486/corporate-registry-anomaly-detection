# Interface Contract — Master Reference
## AI-Based Corporate Registry Anomaly Detection — Yashika & Riya

**Purpose of this document:** This is the one complete, single source of truth for the entire project — every table, every column, every function signature, and who owns what. Since nothing is committed to the repo yet, this replaces every earlier draft. Commit this as `docs/interface_contract.md` before either of you writes a single line of pipeline code.

If you ask any AI tool (me or otherwise) for help on your part, paste the relevant section of this file in as context first — that's what keeps two independently-built halves from drifting apart.

---

## 0. TEAM RESPONSIBILITIES — BALANCED SPLIT

Two tracks, matched in size and difficulty. Each of you owns one track end-to-end; shared items are genuinely shared, not defaulted to one person.

### Yashika — Data & Infrastructure Track
1. Data ingestion pipeline (bulk CSV → raw staging table)
2. Data cleaning & normalization (addresses, names, pincode extraction)
3. Database schema design for **every** table + indexing strategy
4. Blocking strategy implementation (pincode + name-prefix)
5. Hash-chain integrity layer (`record_hashes` + `audit_log`)
6. Cloud deployment & containerization (all services, DB hosting)

### Riya — Intelligence & Application Track
1. Fuzzy matching (Jaro-Winkler / Levenshtein similarity scoring)
2. Graph construction & clustering (NetworkX)
3. Structural feature extraction — all 7 signals (address, name, timing, capital, topology, bridge, category)
4. Isolation Forest anomaly scoring
5. SHAP explainability layer
6. Application layer (the website — search, results, score breakdown display)

### Both — Shared, Non-Splittable Work
- Literature review & Related Work section
- Manual audits of flagged clusters
- Evaluation experiments & results write-up
- Paper writing, poster, presentation, defense prep
- Mentor check-ins and integration testing (running the full pipeline end-to-end together)

**Why this split is balanced:** each track has exactly six owned components, mixing one genuinely hard/novel piece (blocking-at-scale for Yashika, Isolation Forest + SHAP for Riya) with more mechanical, well-defined pieces. Neither track is "just the easy half."

---

## 1. DATABASE SCHEMA CONTRACT

All tables live in the `registry` database. Names are lowercase, snake_case, exactly as written — no pluralizing/depluralizing on your own.

### 1.1 `raw_companies` (Yashika)
Direct, unmodified load of the downloaded MCA CSV.

| Column | Type | Notes |
|---|---|---|
| `raw_id` | SERIAL PRIMARY KEY | |
| `cin` | TEXT | |
| `company_name` | TEXT | |
| `company_status` | TEXT | |
| `company_category` | TEXT | |
| `company_sub_category` | TEXT | |
| `roc_code` | TEXT | |
| `registered_address` | TEXT | |
| `date_of_registration` | TEXT | raw string, unparsed |
| `authorized_capital` | TEXT | raw string, unparsed |
| `paidup_capital` | TEXT | raw string, unparsed |
| `principal_business_activity` | TEXT | |
| `loaded_at` | TIMESTAMP DEFAULT NOW() | |

### 1.2 `cleaned_entities` (Yashika)
One row per company, after normalization. **This is the table Riya's code reads from.**

| Column | Type | Notes |
|---|---|---|
| `entity_id` | SERIAL PRIMARY KEY | used everywhere downstream |
| `raw_id` | INTEGER REFERENCES raw_companies(raw_id) | |
| `cin` | TEXT | |
| `company_name_raw` | TEXT | |
| `company_name_normalized` | TEXT | lowercased, suffix-stripped |
| `address_raw` | TEXT | |
| `address_normalized` | TEXT | abbreviations expanded, punctuation-normalized |
| `pincode` | TEXT | extracted, NULL if not found |
| `company_status` | TEXT | |
| `company_category` | TEXT | |
| `company_sub_category` | TEXT | |
| `authorized_capital` | NUMERIC | parsed to a real number |
| `paidup_capital` | NUMERIC | parsed to a real number |
| `date_of_registration` | DATE | parsed |
| `nic_code` | TEXT | |
| `cleaned_at` | TIMESTAMP DEFAULT NOW() | |

**Naming rule:** any field with both a raw and normalized version follows `<field>_raw` / `<field>_normalized`. No alternate names.

### 1.3 `candidate_pairs` (Yashika)
Output of the blocking step.

| Column | Type | Notes |
|---|---|---|
| `pair_id` | SERIAL PRIMARY KEY | |
| `entity_id_a` | INTEGER REFERENCES cleaned_entities(entity_id) | always the smaller entity_id |
| `entity_id_b` | INTEGER REFERENCES cleaned_entities(entity_id) | always the larger entity_id |
| `blocking_method` | TEXT | `'pincode'` or `'name_prefix'` — insert separate rows if found by both |
| `created_at` | TIMESTAMP DEFAULT NOW() | |

### 1.4 `scored_pairs` (Riya)
One row per candidate pair, with similarity scores.

| Column | Type | Notes |
|---|---|---|
| `pair_id` | INTEGER PRIMARY KEY REFERENCES candidate_pairs(pair_id) | |
| `address_similarity` | FLOAT | Jaro-Winkler, 0.0–1.0 |
| `name_similarity` | FLOAT | Levenshtein-based, 0.0–1.0 |
| `is_match` | BOOLEAN | TRUE if either score clears `MATCH_THRESHOLD` |
| `scored_at` | TIMESTAMP DEFAULT NOW() | |

### 1.5 `graph_edges` (Riya)
Confirmed edges used to build the NetworkX graph.

| Column | Type | Notes |
|---|---|---|
| `edge_id` | SERIAL PRIMARY KEY | |
| `pair_id` | INTEGER REFERENCES scored_pairs(pair_id) | |
| `entity_id_a` | INTEGER | denormalized for query convenience |
| `entity_id_b` | INTEGER | denormalized for query convenience |
| `edge_weight` | FLOAT | max(address_similarity, name_similarity) |

### 1.6 `cluster_assignments` (Yashika persists, Riya's graph output feeds it)

| Column | Type | Notes |
|---|---|---|
| `entity_id` | INTEGER PRIMARY KEY REFERENCES cleaned_entities(entity_id) | |
| `cluster_id` | INTEGER NOT NULL | |
| `assigned_at` | TIMESTAMP DEFAULT NOW() | |

### 1.7 `cluster_scores` (Riya)
One row per cluster, full expanded signal set.

| Column | Type | Notes |
|---|---|---|
| `cluster_id` | INTEGER PRIMARY KEY | |
| `cluster_size` | INTEGER | |
| `address_signal_score` | FLOAT | 0–30 |
| `name_signal_score` | FLOAT | 0–25 |
| `timing_signal_score` | FLOAT | 0–20 |
| `status_signal_score` | FLOAT | 0–10 |
| `capital_similarity_score` | FLOAT | 0–15 — cluster members share suspiciously identical/minimal capital |
| `topology_score` | FLOAT | 0–15 — graph shape: hub-and-spoke vs. chain vs. mesh |
| `bridge_flag` | BOOLEAN | TRUE if this cluster connects to another via one bridging entity |
| `category_homogeneity_score` | FLOAT | 0–10 — unusually narrow shared sub-category |
| `isolation_forest_score` | FLOAT | raw model output over the full feature set |
| `composite_score` | FLOAT | 0–100, combined |
| `flag_category` | TEXT | `'baseline'` / `'moderate'` / `'high_priority'` |
| `scored_at` | TIMESTAMP DEFAULT NOW() | |

### 1.8 `cluster_explanations` (Riya)
SHAP breakdown per cluster — powers the "why was this flagged" view in the app.

| Column | Type | Notes |
|---|---|---|
| `explanation_id` | SERIAL PRIMARY KEY | |
| `cluster_id` | INTEGER REFERENCES cluster_scores(cluster_id) | |
| `feature_name` | TEXT | one of the 7 signal names |
| `shap_value` | FLOAT | signed contribution (positive = toward anomalous) |
| `rank` | INTEGER | 1 = most influential for this cluster |
| `computed_at` | TIMESTAMP DEFAULT NOW() | |

### 1.9 `record_hashes` (Yashika)
Hash-chained integrity record over the source data.

| Column | Type | Notes |
|---|---|---|
| `hash_id` | SERIAL PRIMARY KEY | |
| `entity_id` | INTEGER REFERENCES cleaned_entities(entity_id) | |
| `record_hash` | TEXT | SHA-256 of this entity's key fields |
| `previous_hash` | TEXT | `record_hash` of the row inserted immediately before this one |
| `created_at` | TIMESTAMP DEFAULT NOW() | |

### 1.10 `audit_log` (Yashika)
Hash-chained integrity record over flag/review actions.

| Column | Type | Notes |
|---|---|---|
| `log_id` | SERIAL PRIMARY KEY | |
| `action_type` | TEXT | `'flagged'` / `'reviewed_confirmed'` / `'reviewed_dismissed'` / `'escalated'` |
| `cluster_id` | INTEGER REFERENCES cluster_scores(cluster_id) | |
| `reviewer` | TEXT | who took the action, or `'system'` |
| `action_hash` | TEXT | SHA-256 of (action_type + cluster_id + reviewer + timestamp + previous_hash) |
| `previous_hash` | TEXT | `action_hash` of the row before this one |
| `created_at` | TIMESTAMP DEFAULT NOW() | |

---

## 2. NAMING CONVENTIONS
- **snake_case** everywhere — tables, columns, Python variables
- **IDs**: always `<thing>_id`, never bare `id`
- **Booleans**: prefix `is_` (or a clear verb like `bridge_flag`, kept consistent once chosen)
- **Timestamps**: suffix `_at`
- **No abbreviations** — clarity over brevity

---

## 3. THRESHOLDS AND CONSTANTS
Import from one shared file — never hardcode separately.

| Constant | Value | Meaning |
|---|---|---|
| `MATCH_THRESHOLD` | `0.85` | minimum similarity to count as `is_match = TRUE` |
| `HIGH_PRIORITY_SCORE` | `60` | composite_score cutoff for `'high_priority'` |
| `MODERATE_SCORE` | `30` | composite_score cutoff for `'moderate'` |
| `CAPITAL_SIMILARITY_THRESHOLD` | `0.95` | similarity ratio for "suspiciously identical" capital |
| `BRIDGE_MIN_CLUSTER_SIZE` | `3` | minimum cluster size eligible for bridge detection |
| `TOP_N_SHAP_FEATURES` | `3` | how many top features stored per cluster |

Agree on point allocation across all 7 signals together before hardcoding — update Section 1.7 and this table in the same sitting.

---

## 4. FUNCTION SIGNATURE CONTRACT

### 4.1 Yashika provides

```python
# src/cleaning/db_utils.py
def get_cleaned_entities(conn) -> pandas.DataFrame:
    """Returns all cleaned_entities columns as listed in 1.2."""

def get_candidate_pairs(conn) -> pandas.DataFrame:
    """Returns candidate_pairs: [pair_id, entity_id_a, entity_id_b, blocking_method]"""

def write_cluster_assignments(conn, assignments_df):
    """Input: DataFrame [entity_id, cluster_id]. Writes/upserts into cluster_assignments."""

# src/integrity/hash_chain.py
def compute_record_hash(entity_row, previous_hash: str) -> str:
    """SHA-256 of entity_row's key fields + previous_hash. First record uses previous_hash=''."""

def log_audit_action(conn, action_type: str, cluster_id: int, reviewer: str) -> str:
    """Writes one row to audit_log, auto-chaining from the most recent previous_hash. Returns new hash."""

def verify_chain_integrity(conn, table: str) -> bool:
    """table = 'record_hashes' or 'audit_log'. Recomputes the whole chain; True if intact."""
```

### 4.2 Riya provides

```python
# src/matching/scorer.py
def score_candidate_pairs(pairs_df, entities_df) -> pandas.DataFrame:
    """Output: [pair_id, address_similarity, name_similarity, is_match] matching scored_pairs."""

# src/graph/builder.py
def build_clusters(edges_df) -> pandas.DataFrame:
    """Input: [entity_id_a, entity_id_b, edge_weight]. Output: [entity_id, cluster_id]."""

# src/scoring/anomaly.py
def score_clusters(clusters_df, entities_df) -> pandas.DataFrame:
    """
    Input: clusters_df [entity_id, cluster_id]; entities_df with company_status, nic_code,
    company_category, company_sub_category, authorized_capital, paidup_capital, date_of_registration.
    Output: DataFrame matching the full cluster_scores schema (1.7), all 7 signals + composite_score.
    """

# src/scoring/explain.py
def compute_shap_explanations(model, cluster_features_df) -> pandas.DataFrame:
    """
    Uses shap.TreeExplainer(model) on the same feature matrix used in score_clusters().
    Output: matches cluster_explanations schema (1.8), top TOP_N_SHAP_FEATURES per cluster.
    """

# app/main.py  (Streamlit application)
def load_cluster_view(conn, cluster_id: int) -> dict:
    """
    Queries cluster_scores + cluster_explanations + cleaned_entities for one cluster.
    Returns a dict the app renders: company list, composite_score, flag_category,
    and the ranked SHAP explanation list — this is the single function the UI calls
    per page load, keeping all query logic out of the display code.
    """

def search_company(conn, query: str) -> pandas.DataFrame:
    """
    Searches cleaned_entities by company_name_normalized or cin (partial match).
    Returns matching rows with their cluster_id (if any) for the search results page.
    """
```

### 4.3 Shared constants file

```python
# src/config.py
MATCH_THRESHOLD = 0.85
HIGH_PRIORITY_SCORE = 60
MODERATE_SCORE = 30
CAPITAL_SIMILARITY_THRESHOLD = 0.95
BRIDGE_MIN_CLUSTER_SIZE = 3
TOP_N_SHAP_FEATURES = 3

DB_CONFIG = {
    "host": "localhost", "port": 5432,
    "dbname": "registry", "user": "admin", "password": "admin123"
}
```

---

## 5. APPLICATION LAYER (the website — owned by Riya)

**Tech choice: Streamlit.** It's Python-native (no separate frontend framework to learn), queries the database directly, and a working version is realistically buildable in days, not weeks — the right choice given everything else on both your plates.

**Pages:**
1. **Search page** — text input → calls `search_company()` → shows matching companies with their cluster status
2. **Cluster detail page** — given a `cluster_id` → calls `load_cluster_view()` → shows the company list in that cluster, the composite score, the flag category, and a bar chart of the top SHAP-ranked reasons
3. **Browse/leaderboard page** — shows top flagged clusters ranked by `composite_score`, for open-ended exploration beyond search

**Contract with the database layer:** the app never writes raw SQL inline in the UI code — it only calls `load_cluster_view()` and `search_company()` from `src/scoring/` or a dedicated `app/queries.py`. This keeps query logic testable and in one place instead of scattered across UI code.

---

## 6. IMPLEMENTATION NOTES

**Hash-chaining:** `new_hash = SHA256(record_data + previous_hash)`. Altering any past row breaks every hash after it — `verify_chain_integrity()` catches this. Describe this in your paper as "hash-chained" / "blockchain-inspired," not "a blockchain" — accurate and correctly scoped.

**SHAP + Isolation Forest:** a well-established, published technique — `shap.TreeExplainer` works directly with scikit-learn's `IsolationForest` since it's tree-based. Feed it the same feature matrix used for scoring.

---

## 7. HOW TO USE THIS DOCUMENT

- Commit this at `docs/interface_contract.md` — this is the first commit, before any pipeline code.
- Paste the relevant section into any AI conversation before asking for help on your part.
- New table, column, or cross-boundary function not listed here → stop, add it here together, then code it.
- If something here turns out wrong once you're building — expected, that's normal — update this file and tell your partner immediately, don't quietly diverge.
