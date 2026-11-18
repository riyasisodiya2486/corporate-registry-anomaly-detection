# Riya. APPEND this function to the bottom of app/queries.py (no other change there).
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
