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
FEATURE_LABELS = {
    "address_signal_score": "Shared or very similar addresses",
    "name_signal_score": "Very similar company names",
    "timing_signal_score": "Registered around the same time",
    "capital_similarity_score": "Similar authorized capital",
    "topology_score": "How tightly the group is connected",
    "category_homogeneity_score": "Same type of business",
}
EXAMPLE_SEARCHES = ["nidhi", "cotton industry", "enterprises"]
EXAMPLE_CLUSTERS = {
    804: "Example: moderate flag (4 companies, one address)",
    806: "Example: high priority flag (score 100)",
}


def go(page_name, cluster=None, query=None):
    if cluster is not None:
        st.session_state["selected_cluster"] = int(cluster)
    if query is not None:
        st.session_state["search_query"] = query
    st.session_state["nav_override"] = page_name


if "nav_override" in st.session_state:
    st.session_state["page"] = st.session_state.pop("nav_override")

st.sidebar.title("Registry Anomaly Detection")
page = st.sidebar.radio("Go to", PAGES, key="page")
st.sidebar.caption("New here? Start with Home.")

st.warning("Flags are statistical leads for human review. They are NOT findings of wrongdoing.")

# ---------------------------------------------------------------- HOME
if page == "Home":
    st.title("Corporate Registry Anomaly Detection")
    st.write(
        "Some groups of registered companies look unusually alike: the same address, near-identical "
        "names, registered at nearly the same time. This tool finds such groups (called clusters) in "
        "the ROC Pune company registry and gives each group a score. A high score means the group "
        "deserves a closer human look. It does not mean anything illegal happened."
    )
    try:
        s = get_summary()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Companies analysed", f"{s['companies']:,}")
        c2.metric("Groups found", f"{s['clusters']:,}")
        c3.metric("High priority", f"{s['high']:,}")
        c4.metric("Moderate", f"{s['moderate']:,}")
    except Exception:
        st.caption("Live statistics are temporarily unavailable.")

    st.subheader("How to use it in 3 steps")
    st.markdown(
        "1. **Search** for a company by name or CIN.\n"
        "2. Click **View** next to a result to open its group.\n"
        "3. Read **why it was flagged** and see the other companies in the same group."
    )

    st.subheader("Try it now")
    a, b = st.columns(2)
    with a:
        st.write("Example searches")
        for term in EXAMPLE_SEARCHES:
            st.button(f"Search '{term}'", key=f"home_s_{term}", on_click=go,
                      args=("Search",), kwargs={"query": term})
    with b:
        st.write("Example groups")
        for cid, label in EXAMPLE_CLUSTERS.items():
            st.button(label, key=f"home_c_{cid}", on_click=go,
                      args=("Cluster Detail",), kwargs={"cluster": cid})

    with st.expander("What do these words mean?"):
        st.markdown(
            "- **Cluster / group**: companies that the system believes look alike (shared address, "
            "similar names and so on).\n"
            "- **Score (0-100)**: how unusual the group is compared with all other groups.\n"
            "- **High priority / Moderate / Baseline**: the top, middle and normal range of scores.\n"
            "- **Why it was flagged**: the factors that pushed the score up the most."
        )

# -------------------------------------------------------------- SEARCH
elif page == "Search":
    st.title("Search a Company")
    st.write("Type part of a company name (for example 'nidhi') or a full CIN. Minimum 3 characters.")
    with st.form("search_form"):
        typed = st.text_input(
            "Company name or CIN",
            value=st.session_state.get("search_query", ""),
            placeholder="e.g. cotton industry  or  U65999PN2020PLN195362",
        )
        submitted = st.form_submit_button("Search")
    if submitted:
        st.session_state["search_query"] = typed.strip()

    query = st.session_state.get("search_query", "")
    if not query:
        st.info("Nothing searched yet. Try one of these:")
        cols = st.columns(len(EXAMPLE_SEARCHES))
        for col, term in zip(cols, EXAMPLE_SEARCHES):
            col.button(term, key=f"srch_{term}", on_click=go, args=("Search",), kwargs={"query": term})
    elif len(query) < 3:
        st.info("Please enter at least 3 characters.")
    else:
        results = search_company(query)
        if results.empty:
            st.write(f"No matches for '{query}'. Try a shorter or different part of the name.")
        else:
            st.caption(
                f"Showing up to 25 matches for '{query}'. Companies that belong to a group are listed first. "
                "'Not in any group' is normal: it means no look-alike companies were found."
            )
            h = st.columns([4, 2, 2, 1])
            h[0].markdown("**Company**")
            h[1].markdown("**Group**")
            h[2].markdown("**Score / flag**")
            for _, row in results.iterrows():
                cols = st.columns([4, 2, 2, 1])
                cols[0].write(row["company_name_raw"])
                cols[0].caption(f"CIN {row['cin']}  |  {row['company_status']}")
                has_cluster = pd.notna(row["cluster_id"])
                cols[1].write(f"Group {int(row['cluster_id'])}" if has_cluster else "Not in any group")
                if has_cluster and pd.notna(row["composite_score"]):
                    flag = FLAG_LABELS.get(row["flag_category"], row["flag_category"])
                    cols[2].write(f"{row['composite_score']:.1f} - {flag}")
                else:
                    cols[2].write("-")
                if has_cluster:
                    cols[3].button("View", key=f"view_{int(row['entity_id'])}", on_click=go,
                                   args=("Cluster Detail",), kwargs={"cluster": int(row["cluster_id"])})

# ------------------------------------------------------ CLUSTER DETAIL
elif page == "Cluster Detail":
    st.title("Cluster Detail")
    st.write("A cluster is a group of companies that look alike. Open one from Search, "
             "or type a group number below.")
    auto_load = False
    if "selected_cluster" in st.session_state:
        st.session_state["cluster_input"] = st.session_state.pop("selected_cluster")
        auto_load = True
    cluster_id = st.number_input("Group (cluster) number", min_value=1, step=1, key="cluster_input")
    load_clicked = st.button("Show this group")

    if load_clicked or auto_load:
        data = load_cluster_view(int(cluster_id))
        scores = data["scores"]
        if not scores:
            st.write("No group found with that number. Use Search to find a valid one.")
        else:
            members = data["members"]
            flag = FLAG_LABELS.get(scores.get("flag_category"), scores.get("flag_category"))
            m1, m2, m3 = st.columns(3)
            m1.metric("Score (0-100)", f"{scores['composite_score']:.1f}")
            m2.metric("Flag", flag)
            m3.metric("Companies in group", len(members))

            if scores.get("flag_category") == "high_priority":
                st.error("This group is in the top range of unusual groups. It is a lead for human review.")
            elif scores.get("flag_category") == "moderate":
                st.warning("This group is somewhat unusual. Worth a look if you have time.")
            else:
                st.success("This group is in the normal range.")

            if len(members) > 1 and members["address_raw"].nunique() == 1:
                st.info(f"All {len(members)} companies list the same registered address.")

            st.subheader("Why this was flagged")
            st.caption("Bigger number = that factor pushed the score up more.")
            ex = data["explanations"].copy()
            if not ex.empty:
                ex["Factor"] = ex["feature_name"].map(FEATURE_LABELS).fillna(ex["feature_name"])
                ex = ex.rename(columns={"shap_value": "Influence", "rank": "Rank"})
                st.dataframe(ex[["Rank", "Factor", "Influence"]], hide_index=True)

            st.subheader("Companies in this group")
            mem = members.rename(columns={
                "entity_id": "ID", "company_name_raw": "Company", "address_raw": "Address",
                "company_status": "Status", "authorized_capital": "Authorized capital",
                "date_of_registration": "Registered on"})
            st.dataframe(mem, hide_index=True)
    else:
        st.info("No group selected yet. Try an example:")
        for cid, label in EXAMPLE_CLUSTERS.items():
            st.button(label, key=f"cd_{cid}", on_click=go, args=("Cluster Detail",),
                      kwargs={"cluster": cid})

# --------------------------------------------------------- LEADERBOARD
elif page == "Leaderboard":
    st.title("Top Flagged Groups")
    st.write("Groups ranked by score, highest first.")
    options = {"High priority only": "high_priority", "Moderate only": "moderate",
               "Normal range only": "baseline", "All groups": "all"}
    choice = st.selectbox("Show", list(options.keys()))
    data = get_leaderboard(limit=500)
    if options[choice] != "all":
        data = data[data["flag_category"] == options[choice]]
    shown = data.rename(columns={"cluster_id": "Group", "cluster_size": "Companies",
                                 "composite_score": "Score", "flag_category": "Flag"})
    shown["Flag"] = shown["Flag"].map(FLAG_LABELS).fillna(shown["Flag"])
    st.dataframe(shown, hide_index=True)
    if not data.empty:
        pick = st.selectbox("Open a group", data["cluster_id"].tolist())
        st.button("Open this group", on_click=go, args=("Cluster Detail",),
                  kwargs={"cluster": int(pick)})