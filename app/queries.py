import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])


def search_company(query: str) -> pd.DataFrame:
  with engine.connect() as conn:
    return pd.read_sql(
        text("""
            SELECT e.entity_id, e.company_name_raw, e.cin, e.address_raw, e.company_status,
                   ca.cluster_id, cs.composite_score, cs.flag_category
            FROM cleaned_entities e
            LEFT JOIN cluster_assignments ca ON e.entity_id = ca.entity_id
            LEFT JOIN cluster_scores cs ON ca.cluster_id = cs.cluster_id
            WHERE e.company_name_normalized ILIKE :q OR e.cin ILIKE :q
            LIMIT 25
        """),
        conn,
        params={"q": f"%{query.lower()}%"},
    )


def load_cluster_view(cluster_id: int) -> dict:
  with engine.connect() as conn:
    members = pd.read_sql(
        text("""
            SELECT e.entity_id, e.company_name_raw, e.address_raw, e.company_status,
                   e.authorized_capital, e.date_of_registration
            FROM cleaned_entities e JOIN cluster_assignments ca ON e.entity_id = ca.entity_id
            WHERE ca.cluster_id = :cid
        """),
        conn,
        params={"cid": cluster_id},
    )
    scores = pd.read_sql(
        text("SELECT * FROM cluster_scores WHERE cluster_id = :cid"),
        conn,
        params={"cid": cluster_id},
    )
    explanations = pd.read_sql(
        text("""
            SELECT feature_name, shap_value, rank FROM cluster_explanations
            WHERE cluster_id = :cid ORDER BY rank
        """),
        conn,
        params={"cid": cluster_id},
    )
  return {
      "members": members,
      "scores": scores.iloc[0].to_dict() if not scores.empty else {},
      "explanations": explanations,
  }


def get_leaderboard(limit: int = 50) -> pd.DataFrame:
  with engine.connect() as conn:
    return pd.read_sql(
        text("""
            SELECT cluster_id, cluster_size, composite_score, flag_category
            FROM cluster_scores ORDER BY composite_score DESC LIMIT :lim
        """),
        conn,
        params={"lim": limit},
    )