import os
import pandas as pd
from queries import get_leaderboard, load_cluster_view, search_company
import streamlit as st

st.set_page_config(
    page_title="Corporate Registry Anomaly Detection", layout="wide"
)

# Navigation override logic
default_page = st.session_state.pop("nav_override", "Search")
nav_options = ["Search", "Cluster Detail", "Leaderboard"]
page = st.sidebar.radio(
    "Navigate", nav_options, index=nav_options.index(default_page)
)

if page == "Search":
  st.title("Search a Company")
  query = st.text_input("Enter company name or CIN")
  if query:
    results = search_company(query)
    if results.empty:
      st.write("No matches found.")
    else:
      for _, row in results.iterrows():
        cols = st.columns([3, 2, 2, 1])
        cols[0].write(row["company_name_raw"])
        cols[1].write(
            f"Cluster {row['cluster_id']}"
            if pd.notna(row["cluster_id"])
            else "No cluster"
        )
        cols[2].write(
            f"Score: {row['composite_score']:.1f}"
            if pd.notna(row["composite_score"])
            else "—"
        )
        if pd.notna(row["cluster_id"]) and cols[3].button(
            "View", key=f"view_{row['entity_id']}"
        ):
          st.session_state["selected_cluster"] = int(row["cluster_id"])
          st.session_state["nav_override"] = "Cluster Detail"
          st.rerun()

elif page == "Cluster Detail":
  st.title("Cluster Detail")
  default_id = st.session_state.get("selected_cluster", 1)
  cluster_id = st.number_input(
      "Enter a cluster ID", min_value=1, step=1, value=default_id
  )
  if st.button("Load") or "selected_cluster" in st.session_state:
    st.session_state.pop("selected_cluster", None)
    data = load_cluster_view(int(cluster_id))
    if data["scores"]:
      st.metric("Composite Score", f"{data['scores']['composite_score']:.1f}")
      st.metric("Flag Category", data["scores"]["flag_category"])
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