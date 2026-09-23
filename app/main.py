import streamlit as st

st.set_page_config(page_title="Corporate Registry Anomaly Detection", layout="wide")

page = st.sidebar.radio("Navigate", ["Search", "Cluster Detail", "Leaderboard"])

if page == "Search":
    st.title("Search a Company")
    query = st.text_input("Enter company name or CIN")
    st.write("Results will appear here once connected to the database.")

elif page == "Cluster Detail":
    st.title("Cluster Detail")
    st.write("Company list, composite score, and SHAP-based explanation will appear here.")

elif page == "Leaderboard":
    st.title("Top Flagged Clusters")
    st.write("Ranked list of clusters will appear here.")