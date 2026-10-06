import streamlit as st
from queries import get_leaderboard, load_cluster_view, search_company

st.set_page_config(
    page_title="Corporate Registry Anomaly Detection", layout="wide"
)
page = st.sidebar.radio("Navigate", ["Search", "Cluster Detail", "Leaderboard"])

if page == "Search":
  st.title("Search a Company")
  query = st.text_input("Enter company name or CIN")
  if query:
    results = search_company(query)
    if results.empty:
      st.write("No matches found.")
    else:
      st.dataframe(results)

elif page == "Cluster Detail":
  st.title("Cluster Detail")
  cluster_id = st.number_input("Enter a cluster ID", min_value=1, step=1)
  if st.button("Load"):
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
  st.dataframe(get_leaderboard())