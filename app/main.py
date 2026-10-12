import pandas as pd
import streamlit as st
from queries import get_leaderboard, get_summary, load_cluster_view, search_company

st.set_page_config(page_title="Corporate Registry Anomaly Detection", layout="wide")

PAGES = ["Home", "Search", "Cluster Detail", "Leaderboard"]

FLAG_LABELS = {
    "high_priority": "High priority",
    "moderate": "Moderate",
    "baseline": "Baseline (normal range)",
}

if "nav_override" in st.session_state:
    st.session_state["page"] = st.session_state.pop("nav_override")

page = st.sidebar.radio("Navigate", PAGES, key="page")

if page == "Home":
    st.title("Corporate Registry Anomaly Detection")
    summary = get_summary()
    cols = st.columns(4)
    cols[0].metric("Companies", summary["companies"])
    cols[1].metric("Clusters", summary["clusters"])
    cols[2].metric("High priority", summary["high"])
    cols[3].metric("Moderate", summary["moderate"])
    st.info("Structural anomaly flags are statistical leads for human review, not findings of wrongdoing.")

elif page == "Search":
    st.title("Search a Company")
    with st.form("search_form"):
        typed = st.text_input("Enter company name or CIN (at least 3 characters)")
        submitted = st.form_submit_button("Search")
    if submitted:
        st.session_state["search_query"] = typed.strip()

    query = st.session_state.get("search_query", "")
    if query:
        if len(query) < 3:
            st.info("Please enter at least 3 characters.")
        else:
            results = search_company(query)
            st.caption(f"Showing up to 25 matches for: {query}")
            if results.empty:
                st.write("No matches found.")
            for _, row in results.iterrows():
                cols = st.columns([3, 2, 2, 1])
                cols[0].write(row["company_name_raw"])
                has_cluster = pd.notna(row["cluster_id"])
                cols[1].write(f"Cluster {int(row['cluster_id'])}" if has_cluster else "No cluster")
                cols[2].write(
                    f"Score: {row['composite_score']:.1f}"
                    if pd.notna(row["composite_score"])
                    else "-"
                )
                if has_cluster and cols[3].button("View", key=f"view_{int(row['entity_id'])}"):
                    st.session_state["selected_cluster"] = int(row["cluster_id"])
                    st.session_state["nav_override"] = "Cluster Detail"
                    st.rerun()

elif page == "Cluster Detail":
    st.title("Cluster Detail")
    auto_load = False
    if "selected_cluster" in st.session_state:
        st.session_state["cluster_input"] = st.session_state.pop("selected_cluster")
        auto_load = True
    cluster_id = st.number_input("Enter a cluster ID", min_value=1, step=1, key="cluster_input")
    load_clicked = st.button("Load")
    if load_clicked or auto_load:
        data = load_cluster_view(int(cluster_id))
        if data["scores"]:
            st.metric("Composite Score", f"{data['scores']['composite_score']:.1f}")
            st.metric("Flag Category", FLAG_LABELS.get(
                data["scores"]["flag_category"], data["scores"]["flag_category"]
            ))
            st.subheader("Why this was flagged")
            st.dataframe(data["explanations"])
            st.subheader("Cluster Members")
            st.dataframe(data["members"])
        else:
            st.write("No data found for this cluster ID.")

elif page == "Leaderboard":
    st.title("Top Flagged Clusters")
    filter_choice = st.selectbox("Show", ["high_priority", "moderate", "all"])
    data = get_leaderboard(limit=500)
    if filter_choice != "all":
        data = data[data["flag_category"] == filter_choice]
    st.dataframe(data)
