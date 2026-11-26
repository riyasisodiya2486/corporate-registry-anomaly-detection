import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# Real columns of reviewer_reviews (from show_schema.py).
CHECK_COLUMNS = [
    "duplicate_record", "address_type", "registered_close",
    "directors_shared", "filings_ok", "office_exists",
]
VERDICTS = ["worth_review", "ordinary", "data_artifact", "need_more_info"]
BLIND_MODE = "blind_queue"
OPEN_MODE = "open"
RUN_TAG = os.environ.get("REVIEW_RUN_TAG", "v2")


def _secret(key):
    # Touch st.secrets only when nothing else was found: Streamlit draws a red
    # error box when no secrets.toml exists.
    try:
        return st.secrets[key]
    except Exception:
        return None


def _database_url():
    # Order: APP_DATABASE_URL (V2 app_reader, local), DATABASE_URL, then st.secrets.
    for key in ("APP_DATABASE_URL", "DATABASE_URL"):
        url = os.environ.get(key)
        if url:
            return url
    return _secret("APP_DATABASE_URL") or _secret("DATABASE_URL")


def _reviewer_url():
    return os.environ.get("REVIEWER_DATABASE_URL") or _secret("REVIEWER_DATABASE_URL")


def reviewer_passcode():
    return os.environ.get("REVIEWER_PASSCODE") or _secret("REVIEWER_PASSCODE") or ""


def reviewer_enabled() -> bool:
    """False unless BOTH reviewer values exist. Then the app behaves exactly like v1."""
    return bool(_reviewer_url() and reviewer_passcode())


@st.cache_resource
def get_engine():
    url = _database_url()
    if not url:
        raise RuntimeError(
            "No database URL found. Add DATABASE_URL to Streamlit Secrets (deployed) "
            "or APP_DATABASE_URL / DATABASE_URL to .env (local)."
        )
    # pool_pre_ping recovers connections that Neon put to sleep
    return create_engine(url, pool_pre_ping=True, pool_recycle=300)


@st.cache_resource
def get_reviewer_engine():
    url = _reviewer_url()
    if not url:
        raise RuntimeError("REVIEWER_DATABASE_URL not set.")
    return create_engine(url, pool_pre_ping=True, pool_recycle=300)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@st.cache_data(ttl=600, show_spinner="Searching...")
def search_company(query: str) -> pd.DataFrame:
    raw = query.strip()
    q = _escape_like(raw.lower())
    with get_engine().connect() as conn:
        return pd.read_sql(text("""
            SELECT e.entity_id, e.company_name_raw, e.cin, e.address_raw, e.company_status,
                   ca.cluster_id, cs.composite_score, cs.flag_category
            FROM cleaned_entities e
            LEFT JOIN cluster_assignments ca ON e.entity_id = ca.entity_id
            LEFT JOIN cluster_scores cs ON ca.cluster_id = cs.cluster_id
            WHERE e.company_name_normalized ILIKE :contains OR e.cin = :cin
            ORDER BY (ca.cluster_id IS NULL) ASC,
                     COALESCE(e.company_name_normalized ILIKE :prefix, FALSE) DESC,
                     e.company_name_normalized ASC NULLS LAST,
                     e.entity_id ASC
            LIMIT 25
        """), conn, params={"contains": f"%{q}%", "prefix": f"{q}%", "cin": raw.upper()})


@st.cache_data(ttl=600, show_spinner=False)
def load_cluster_view(cluster_id: int) -> dict:
    with get_engine().connect() as conn:
        members = pd.read_sql(text("""
            SELECT e.entity_id, e.company_name_raw, e.address_raw, e.company_status,
                   e.authorized_capital, e.date_of_registration
            FROM cleaned_entities e JOIN cluster_assignments ca ON e.entity_id = ca.entity_id
            WHERE ca.cluster_id = :cid
            ORDER BY e.entity_id
        """), conn, params={"cid": cluster_id})
        scores = pd.read_sql(text("SELECT * FROM cluster_scores WHERE cluster_id = :cid"),
                             conn, params={"cid": cluster_id})
        explanations = pd.read_sql(text("""
            SELECT feature_name, shap_value, rank FROM cluster_explanations
            WHERE cluster_id = :cid ORDER BY rank
        """), conn, params={"cid": cluster_id})
    return {"members": members,
            "scores": scores.iloc[0].to_dict() if not scores.empty else {},
            "explanations": explanations}


@st.cache_data(ttl=600, show_spinner=False)
def get_leaderboard(flag: str = "all", limit: int = 500) -> pd.DataFrame:
    # The flag filter runs in SQL BEFORE the limit, so each category gets its own top-N.
    with get_engine().connect() as conn:
        return pd.read_sql(text("""
            SELECT cluster_id, cluster_size, composite_score, flag_category
            FROM cluster_scores
            WHERE (:flag = 'all' OR flag_category = :flag)
            ORDER BY composite_score DESC, cluster_id ASC
            LIMIT :lim
        """), conn, params={"flag": flag, "lim": limit})


@st.cache_data(ttl=600, show_spinner=False)
def get_summary() -> dict:
    with get_engine().connect() as conn:
        companies = conn.execute(text("SELECT COUNT(*) FROM cleaned_entities")).scalar()
        flags = pd.read_sql(text(
            "SELECT flag_category, COUNT(*) AS n FROM cluster_scores GROUP BY flag_category"), conn)
    counts = dict(zip(flags["flag_category"], flags["n"]))
    return {"companies": int(companies),
            "clusters": int(sum(counts.values())),
            "high": int(counts.get("high_priority", 0)),
            "moderate": int(counts.get("moderate", 0)),
            "baseline": int(counts.get("baseline", 0))}


@st.cache_data(ttl=600, show_spinner=False)
def load_cluster_extras(cluster_id: int) -> dict:
    with get_engine().connect() as conn:
        members = pd.read_sql(text("""
            SELECT e.entity_id, e.company_name_raw, e.company_name_normalized, e.address_normalized,
                   e.company_status, e.date_of_registration
            FROM cleaned_entities e JOIN cluster_assignments ca ON e.entity_id = ca.entity_id
            WHERE ca.cluster_id = :cid ORDER BY e.entity_id
        """), conn, params={"cid": cluster_id})
        reuse = pd.read_sql(text("""
            SELECT e.address_normalized, COUNT(DISTINCT ca2.cluster_id) AS n_clusters
            FROM cleaned_entities e
            JOIN cluster_assignments ca  ON ca.entity_id = e.entity_id AND ca.cluster_id = :cid
            JOIN cleaned_entities e2     ON e2.address_normalized = e.address_normalized
            JOIN cluster_assignments ca2 ON ca2.entity_id = e2.entity_id
            GROUP BY e.address_normalized
        """), conn, params={"cid": cluster_id})
    return {"members": members, "reuse": reuse}


# ------------------------------------------------------------------
# Reviewer functions (V2). Not cached: they must always see fresh rows.
# Reviews are INSERT only. chain_hash stays NULL; chain_reviews.py fills it later.
# ------------------------------------------------------------------
def save_review(review_round: str, review_mode: str, cluster_id: int, reviewer: str,
                answers: dict, verdict: str, note: str) -> int:
    if verdict not in VERDICTS:
        raise ValueError("Invalid verdict")
    if review_mode not in (BLIND_MODE, OPEN_MODE):
        raise ValueError("Invalid review mode")
    cols = ["cluster_id", "reviewer", "review_mode", "verdict"] + CHECK_COLUMNS + \
           ["note", "run_tag", "review_round"]
    params = {"cluster_id": int(cluster_id), "reviewer": reviewer, "review_mode": review_mode,
              "verdict": verdict, "note": (note or "").strip()[:500],
              "run_tag": RUN_TAG, "review_round": review_round}
    for k in CHECK_COLUMNS:
        params[k] = answers[k]
    # Column names come from the constants above, never from user input.
    sql = (f"INSERT INTO reviewer_reviews ({', '.join(cols)}) "
           f"VALUES ({', '.join(':' + c for c in cols)}) RETURNING review_id")

    with get_reviewer_engine().begin() as conn:
        if review_mode == BLIND_MODE:
            existing = conn.execute(text("""
                SELECT review_id FROM reviewer_reviews
                WHERE cluster_id = :c AND reviewer = :r AND review_round = :rd
                  AND review_mode = 'blind_queue' LIMIT 1"""),
                {"c": int(cluster_id), "r": reviewer, "rd": review_round}).first()
            if existing:
                return int(existing[0])      # double click: already saved
        new_id = conn.execute(text(sql), params).scalar()
    if new_id is None:
        raise RuntimeError("Insert returned no row id")
    return int(new_id)


def next_queue_cluster(batch: str, reviewer: str):
    """Next cluster this reviewer has not blind-reviewed in this batch. Order is
    md5(cluster_id || reviewer): the same clusters for everyone, a different repeatable order each."""
    with get_reviewer_engine().connect() as conn:
        row = conn.execute(text("""
            SELECT q.cluster_id
            FROM review_queue q
            WHERE q.batch = :b
              AND NOT EXISTS (
                  SELECT 1 FROM reviewer_reviews r
                  WHERE r.cluster_id = q.cluster_id
                    AND r.reviewer = :rev
                    AND r.review_round = :b
                    AND r.review_mode = 'blind_queue')
            ORDER BY md5(CAST(q.cluster_id AS text) || :rev), q.cluster_id
            LIMIT 1
        """), {"b": batch, "rev": reviewer}).first()
    return int(row[0]) if row else None


def reviewer_progress(batch: str, reviewer: str):
    """Returns (done, total) for this reviewer in this batch."""
    with get_reviewer_engine().connect() as conn:
        row = conn.execute(text("""
            SELECT
              (SELECT COUNT(DISTINCT cluster_id) FROM reviewer_reviews
                WHERE review_round = :b AND reviewer = :rev AND review_mode = 'blind_queue') AS done,
              (SELECT COUNT(*) FROM review_queue WHERE batch = :b) AS total
        """), {"b": batch, "rev": reviewer}).first()
    return int(row[0]), int(row[1])

def get_reviews(batch: str):
    """All blind reviews of a batch. Call only after the viewer finished their own queue."""
    with get_reviewer_engine().connect() as conn:
        return pd.read_sql(text("""
            SELECT cluster_id, reviewer, verdict, duplicate_record, address_type,
                   registered_close, directors_shared, filings_ok, office_exists,
                   note, created_at
            FROM reviewer_reviews
            WHERE review_round = :b AND review_mode = 'blind_queue'
            ORDER BY cluster_id, reviewer
        """), conn, params={"b": batch})

@st.cache_data(ttl=600, show_spinner=False)
def get_ai_opinion(cluster_id: int):
    """Cached AI opinion for a cluster, or None. Read-only; the app never calls Groq."""
    try:
        with get_engine().connect() as conn:
            row = conn.execute(text("""
                SELECT verdict, duplicate_record, address_type, registered_close,
                       directors_shared, filings_ok, office_exists, reason, model
                FROM ai_opinions WHERE cluster_id = :c"""), {"c": int(cluster_id)}).mappings().first()
        return dict(row) if row else None
    except Exception:
        return None

@st.cache_data(ttl=600, show_spinner=False)
def get_human_summary(cluster_id: int):
    try:
        with get_engine().connect() as conn:
            row = conn.execute(text("""SELECT final_verdict, n_reviewers, reviewers_agreed
                FROM human_summary WHERE cluster_id = :c"""), {"c": int(cluster_id)}).mappings().first()
        return dict(row) if row else None
    except Exception:
        return None