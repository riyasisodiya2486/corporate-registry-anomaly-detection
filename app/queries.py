import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


def _database_url():
    # Local: .env / environment first. Only touch st.secrets if nothing is found,
    # because Streamlit draws a red error box when no secrets.toml exists.
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        return None


@st.cache_resource
def get_engine():
    url = _database_url()
    if not url:
        raise RuntimeError("DATABASE_URL not found. Add it to Streamlit Secrets (deployed) or .env (local).")
    # pool_pre_ping recovers connections that Neon put to sleep
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