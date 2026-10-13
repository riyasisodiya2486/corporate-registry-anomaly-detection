
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

st.warning(
    "Flags are statistical leads for human review. "
    "They are NOT findings of wrongdoing."
)

# HOME
if page == "Home":
    st.title("Corporate Registry Anomaly Detection")
    st.write(
        "Some groups of registered companies look unusually alike: they may share "
        "addresses, similar names, or registration dates. This tool finds such groups "
        "(called clusters) in the ROC Pune company registry and assigns each group a score. "
        "A high score means the group deserves closer human review, not that anything "
        "illegal happened."
    )

    try:
        summary = get_summary()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Companies analysed", f"{summary['companies']:,}")
        c2.metric("Groups found", f"{summary['clusters']:,}")
        c3.metric("High priority", f"{summary['high']:,}")
        c4.metric("Moderate", f"{summary['moderate']:,}")
    except Exception:
        st.caption("Live statistics are temporarily unavailable.")

    st.subheader("How to use it")
    st.markdown(
        "1. **Search** for a company by name or CIN.\n"
        "2. Click **View** next to a result to open its group.\n"
        "3. Review the score, contributing factors, and other companies in the group."
    )

    left, right = st.columns(2)
    with left:
        st.write("Example searches")
        for term in EXAMPLE_SEARCHES:
            st.button(
                f"Search '{term}'",
                key=f"home_search_{term}",
                on_click=go,
                args=("Search",),
                kwargs={"query": term},
            )
    with right:
        st.write("Example groups")
        for cluster_id, label in EXAMPLE_CLUSTERS.items():
            st.button(
                label,
                key=f"home_cluster_{cluster_id}",
                on_click=go,
                args=("Cluster Detail",),
                kwargs={"cluster": cluster_id},
            )

    with st.expander("Glossary"):
        st.markdown(
            "- **Cluster / group:** companies the system identifies as structurally similar.\n"
            "- **Score (0–100):** a relative measure of how unusual a group appears.\n"
            "- **Flag:** a priority category for human review.\n"
            "- **Why flagged:** the factors that contributed to the score."
        )

# SEARCH
elif page == "Search":
    st.title("Search a Company")
    st.write("Search by part of a company name or a full CIN. Enter at least 3 characters.")

    with st.form("search_form"):
        typed = st.text_input(
            "Company name or CIN",
            value=st.session_state.get("search_query", ""),
            placeholder="e.g. nidhi or a company CIN",
        )
        submitted = st.form_submit_button("Search")

    if submitted:
        st.session_state["search_query"] = typed.strip()

    query = st.session_state.get("search_query", "")

    if not query:
        st.info("Nothing searched yet. Try an example:")
        cols = st.columns(len(EXAMPLE_SEARCHES))
        for col, term in zip(cols, EXAMPLE_SEARCHES):
            col.button(
                term,
                key=f"search_example_{term}",
                on_click=go,
                args=("Search",),
                kwargs={"query": term},
            )
    elif len(query) < 3:
        st.info("Please enter at least 3 characters.")
    else:
        results = search_company(query)
        if results.empty:
            st.write(f"No matches for '{query}'. Try a different search.")
        else:
            st.caption(
                f"Showing up to 25 matches for '{query}'. Companies in groups appear first. "
                "'Not in any group' means no look-alike group was found for that company."
            )

            for _, row in results.iterrows():
                cols = st.columns([4, 2, 2, 1])
                cols[0].write(row["company_name_raw"])
                cols[0].caption(f"CIN {row['cin']} | {row['company_status']}")

                cluster_id = row["cluster_id"]
                has_cluster = pd.notna(cluster_id)

                cols[1].write(
                    f"Group {int(cluster_id)}" if has_cluster else "Not in any group"
                )

                if has_cluster and pd.notna(row["composite_score"]):
                    flag = FLAG_LABELS.get(
                        row["flag_category"], row["flag_category"]
                    )
                    cols[2].write(f"{row['composite_score']:.1f} — {flag}")
                else:
                    cols[2].write("—")

                if has_cluster:
                    cols[3].button(
                        "View",
                        key=f"view_{int(row['entity_id'])}",
                        on_click=go,
                        args=("Cluster Detail",),
                        kwargs={"cluster": int(cluster_id)},
                    )

# CLUSTER DETAIL
elif page == "Cluster Detail":
    st.title("Cluster Detail")
    st.write(
        "A cluster is a group of companies that look alike. Open one from Search "
        "or enter a group number below."
    )

    auto_load = False
    if "selected_cluster" in st.session_state:
        st.session_state["cluster_input"] = st.session_state.pop("selected_cluster")
        auto_load = True

    cluster_id = st.number_input(
        "Group (cluster) number",
        min_value=1,
        step=1,
        key="cluster_input",
    )
    load_clicked = st.button("Show this group")

    if load_clicked or auto_load:
        data = load_cluster_view(int(cluster_id))
        scores = data["scores"]

        if not scores:
            st.info("No group found with that number. Search for a company to find a valid group.")
        else:
            members = data["members"]
            flag = FLAG_LABELS.get(
                scores.get("flag_category"), scores.get("flag_category")
            )

            m1, m2, m3 = st.columns(3)
            m1.metric("Score (0–100)", f"{scores['composite_score']:.1f}")
            m2.metric("Flag", flag)
            m3.metric("Companies in group", len(members))

            if scores.get("flag_category") == "high_priority":
                st.warning("This group is unusually scored and is a lead for human review.")
            elif scores.get("flag_category") == "moderate":
                st.info("This group is somewhat unusual and may merit review.")
            else:
                st.success("This group is in the baseline score range.")


            if len(members) > 1:
                addresses = (
                    members["address_raw"]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.replace(r"\s+", " ", regex=True)
                    .str.strip()
                )
                addresses = addresses[ addresses != "" ]
                repeated_address = addresses.value_counts()

                if not repeated_address.empty and repeated_address.max() > 1:
                    st.info(
                        f"{repeated_address.max()} companies share the same "
                        "registered address (after basic text normalization)."
                    )


            st.subheader("Why this was flagged")
            st.caption("A larger influence value means the factor contributed more.")
            explanations = data["explanations"].copy()

            if not explanations.empty:
                explanations["Factor"] = (
                    explanations["feature_name"]
                    .map(FEATURE_LABELS)
                    .fillna(explanations["feature_name"])
                )
                explanations = explanations.rename(
                    columns={"shap_value": "Influence", "rank": "Rank"}
                )
                st.dataframe(
                    explanations[["Rank", "Factor", "Influence"]],
                    hide_index=True,
                )
            else:
                st.info("No explanation details are available for this group.")

            st.subheader("Companies in this group")
            display_members = members.rename(
                columns={
                    "entity_id": "ID",
                    "company_name_raw": "Company",
                    "address_raw": "Address",
                    "company_status": "Status",
                    "authorized_capital": "Authorized capital",
                    "date_of_registration": "Registered on",
                }
            )
            st.dataframe(display_members, hide_index=True)

    else:
        st.info("No group selected yet. Try an example:")
        for cluster_id, label in EXAMPLE_CLUSTERS.items():
            st.button(
                label,
                key=f"detail_example_{cluster_id}",
                on_click=go,
                args=("Cluster Detail",),
                kwargs={"cluster": cluster_id},
            )

# LEADERBOARD
elif page == "Leaderboard":
    st.title("Top Flagged Groups")
    st.write("Groups ranked by score, highest first.")

    options = {
        "High priority only": "high_priority",
        "Moderate only": "moderate",
        "Normal range only": "baseline",
        "All groups": "all",
    }
    choice = st.selectbox("Show", list(options.keys()))
    data = get_leaderboard(limit=500)

    if options[choice] != "all":
        data = data[data["flag_category"] == options[choice]]

    shown = data.rename(
        columns={
            "cluster_id": "Group",
            "cluster_size": "Companies",
            "composite_score": "Score",
            "flag_category": "Flag",
        }
    )
    shown["Flag"] = shown["Flag"].map(FLAG_LABELS).fillna(shown["Flag"])
    st.dataframe(shown, hide_index=True)

    if not data.empty:
        pick = st.selectbox("Open a group", data["cluster_id"].tolist())
        st.button(
            "Open this group",
            on_click=go,
            args=("Cluster Detail",),
            kwargs={"cluster": int(pick)},
        )
