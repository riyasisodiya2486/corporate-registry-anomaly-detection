import pandas as pd
import streamlit as st
from queries import get_leaderboard, get_summary, load_cluster_view, search_company

st.set_page_config(
    page_title="ROC Pune | Corporate Registry Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@300;400;500;600;700&display=swap');

    .main, .stApp {
        background-color: #07090E !important;
        font-family: 'Inter', sans-serif;
        color: #E2E8F0;
    }

    /* Hide the menu and footer, but keep the header so the sidebar toggle works on phones */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent !important;}
    [data-testid="stToolbar"] {visibility: hidden;}

    section[data-testid="stSidebar"] {
        background-color: #0B0F17 !important;
        border-right: 1px solid #161F30;
    }
    section[data-testid="stSidebar"] .stRadio label {
        color: #94A3B8 !important;
        font-weight: 500;
        font-size: 0.9rem;
    }
    section[data-testid="stSidebar"] .stRadio label:hover {
        color: #FFFFFF !important;
    }

    h1 {
        color: #F8FAFC !important;
        font-weight: 700 !important;
        font-size: 1.85rem !important;
        letter-spacing: -0.03em;
    }
    h2, h3 {
        color: #F8FAFC !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
    }

    div[data-testid="stMetric"] {
        background: #0D131F;
        border: 1px solid #1B2A4A;
        border-radius: 6px;
        padding: 16px 20px;
    }
    div[data-testid="stMetricLabel"] {
        color: #64748B !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #38BDF8 !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace;
    }

    .stButton>button {
        background-color: #0D131F !important;
        color: #CBD5E1 !important;
        border: 1px solid #1B2A4A !important;
        border-radius: 5px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        padding: 0.45rem 1rem !important;
        transition: all 0.1s ease !important;
    }
    .stButton>button:hover {
        background-color: #162238 !important;
        border-color: #38BDF8 !important;
        color: #FFFFFF !important;
    }

    .stFormSubmitButton>button {
        background-color: #0284C7 !important;
        color: #FFFFFF !important;
        border: 1px solid #0284C7 !important;
        font-weight: 600 !important;
    }
    .stFormSubmitButton>button:hover {
        background-color: #0369A1 !important;
    }

    .tag-high {
        background-color: rgba(239, 68, 68, 0.12);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
    }
    .tag-mod {
        background-color: rgba(245, 158, 11, 0.12);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
    }
    .tag-base {
        background-color: rgba(16, 185, 129, 0.12);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #1B2A4A;
        border-radius: 6px;
        background-color: #0D131F;
    }

    input {
        background-color: #0D131F !important;
        color: #FFFFFF !important;
        border: 1px solid #1B2A4A !important;
        border-radius: 5px !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

PAGES = ["Home", "Search", "Cluster Detail", "Leaderboard"]

FLAG_LABELS = {
    "high_priority": "High Priority",
    "moderate": "Moderate",
    "baseline": "Baseline Range",
}
FEATURE_LABELS = {
    "address_signal_score": "Shared / Similar Addresses",
    "name_signal_score": "Very Similar Company Names",
    "timing_signal_score": "Registered Around the Same Time",
    "capital_similarity_score": "Similar Authorized Capital",
    "topology_score": "How Tightly the Group Is Connected",
    "category_homogeneity_score": "Same Type of Business",
}
EXAMPLE_SEARCHES = ["nidhi", "cotton industry", "enterprises"]
EXAMPLE_CLUSTERS = {
    804: "Cluster #804 (example: shared address)",
    806: "Cluster #806 (example: top score)",
}


def go(page_name, cluster=None, query=None):
    if cluster is not None:
        st.session_state["selected_cluster"] = int(cluster)
    if query is not None:
        st.session_state["search_query"] = query
    st.session_state["nav_override"] = page_name


if "nav_override" in st.session_state:
    st.session_state["page"] = st.session_state.pop("nav_override")

# Sidebar
st.sidebar.markdown(
    """
    <div style="padding: 16px 0 24px 0; border-bottom: 1px solid #161F30; margin-bottom: 12px;">
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #38BDF8; letter-spacing: 0.15em; text-transform: uppercase;">ROC PUNE REGISTRY</div>
        <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC; margin-top: 4px;">Anomaly Intelligence</div>
    </div>
""",
    unsafe_allow_html=True,
)

page = st.sidebar.radio("Navigation", PAGES, key="page")
st.sidebar.caption("New here? Start with Home.")

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="color: #64748B; font-size: 0.72rem; line-height: 1.5; font-family: 'JetBrains Mono', monospace;">
        <span style="color: #FBBF24;">[NOTICE]</span> Automated statistical leads for human review. Not findings of wrongdoing or non-compliance.
    </div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- HOME
if page == "Home":
    st.markdown(
        """
        <div style="padding: 12px 0 24px 0;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #38BDF8; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 6px;">SYSTEM OVERVIEW</div>
            <h1 style="margin: 0; font-size: 2rem;">Corporate Registry Anomaly Intelligence</h1>
            <p style="color: #94A3B8; font-size: 0.95rem; max-width: 800px; margin-top: 8px; line-height: 1.6;">
                This tool finds unusual groups of look-alike companies in the ROC Pune registry
                (shared addresses, near-identical names, registered at nearly the same time) and
                gives each group a score. A high score means the group deserves a closer human look.
                It does not mean anything illegal happened.
            </p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    try:
        s = get_summary()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Companies Analysed", f"{s['companies']:,}")
        c2.metric("Groups (Clusters) Found", f"{s['clusters']:,}")
        c3.metric("High Priority", f"{s['high']:,}")
        c4.metric("Moderate", f"{s['moderate']:,}")
    except Exception:
        st.caption("Live statistics are temporarily unavailable.")

    st.markdown(
        "<h3 style='margin-top: 36px; font-size: 1.1rem; font-family: JetBrains Mono, monospace; color: #64748B;'>HOW TO USE IT</h3>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            "<div style='background: #0D131F; border: 1px solid #1B2A4A; border-radius: 6px; padding: 18px; height: 100%;'>"
            "<div style='font-family: JetBrains Mono; font-size: 0.75rem; color: #38BDF8;'>01 / SEARCH</div>"
            "<div style='font-weight: 600; margin-top: 8px; margin-bottom: 6px;'>Find a company</div>"
            "<div style='color: #94A3B8; font-size: 0.85rem;'>Type part of a company name or a full CIN.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            "<div style='background: #0D131F; border: 1px solid #1B2A4A; border-radius: 6px; padding: 18px; height: 100%;'>"
            "<div style='font-family: JetBrains Mono; font-size: 0.75rem; color: #38BDF8;'>02 / INSPECT</div>"
            "<div style='font-weight: 600; margin-top: 8px; margin-bottom: 6px;'>Open its group</div>"
            "<div style='color: #94A3B8; font-size: 0.85rem;'>See the other companies in the same group and why the group was flagged.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            "<div style='background: #0D131F; border: 1px solid #1B2A4A; border-radius: 6px; padding: 18px; height: 100%;'>"
            "<div style='font-family: JetBrains Mono; font-size: 0.75rem; color: #38BDF8;'>03 / PRIORITIZE</div>"
            "<div style='font-weight: 600; margin-top: 8px; margin-bottom: 6px;'>Browse the leaderboard</div>"
            "<div style='color: #94A3B8; font-size: 0.85rem;'>See groups ranked by score, highest first.</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<h3 style='margin-top: 36px; font-size: 1.1rem; font-family: JetBrains Mono, monospace; color: #64748B;'>TRY IT NOW</h3>",
        unsafe_allow_html=True,
    )
    a, b = st.columns(2)
    with a:
        st.markdown("<div style='font-size: 0.85rem; color: #94A3B8; margin-bottom: 8px;'>Example searches</div>", unsafe_allow_html=True)
        for term in EXAMPLE_SEARCHES:
            st.button(
                f"Search '{term}'",
                key=f"home_s_{term}",
                on_click=go,
                args=("Search",),
                kwargs={"query": term},
                use_container_width=True,
            )
    with b:
        st.markdown("<div style='font-size: 0.85rem; color: #94A3B8; margin-bottom: 8px;'>Example clusters</div>", unsafe_allow_html=True)
        for cid, label in EXAMPLE_CLUSTERS.items():
            st.button(
                f"Open {label}",
                key=f"home_c_{cid}",
                on_click=go,
                args=("Cluster Detail",),
                kwargs={"cluster": cid},
                use_container_width=True,
            )

    with st.expander("What do these words mean?"):
        st.markdown(
            "- **Cluster / group**: companies that the system believes look alike (shared address, "
            "similar names and so on).\n"
            "- **Score (0-100)**: how unusual the group is compared with all other groups.\n"
            "- **High priority / Moderate / Baseline**: the top 5%, the next 15%, and the remaining 80% of scores.\n"
            "- **Why it was flagged**: the factors that pushed the score up the most."
        )

# -------------------------------------------------------------- SEARCH
elif page == "Search":
    st.markdown(
        """
        <div style="padding: 12px 0 16px 0;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #38BDF8; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px;">SEARCH</div>
            <h1 style="margin: 0; font-size: 1.8rem;">Search a Company</h1>
        </div>
    """,
        unsafe_allow_html=True,
    )
    st.write("Type part of a company name (for example 'nidhi') or a full CIN. Minimum 3 characters.")

    with st.form("search_form"):
        col1, col2 = st.columns([5, 1])
        with col1:
            typed = st.text_input(
                "Search Term",
                value=st.session_state.get("search_query", ""),
                placeholder="Enter a company name or a 21-character CIN...",
                label_visibility="collapsed",
            )
        with col2:
            submitted = st.form_submit_button("Search", use_container_width=True)

    if submitted:
        st.session_state["search_query"] = typed.strip()

    query = st.session_state.get("search_query", "")
    if not query:
        st.info("Nothing searched yet. Try one of these:")
        cols = st.columns(len(EXAMPLE_SEARCHES))
        for col, term in zip(cols, EXAMPLE_SEARCHES):
            col.button(
                term,
                key=f"srch_{term}",
                on_click=go,
                args=("Search",),
                kwargs={"query": term},
                use_container_width=True,
            )
    elif len(query) < 3:
        st.warning("Please enter at least 3 characters.")
    else:
        results = search_company(query)
        if results.empty:
            st.warning(f"No matches for '{query}'. Try a shorter or different part of the name.")
        else:
            st.caption(
                f"Showing up to 25 matches for '{query}'. Companies that belong to a group are listed first. "
                "'Not in any group' is normal: it means no look-alike companies were found."
            )
            for _, row in results.iterrows():
                with st.container():
                    cols = st.columns([4, 2, 2, 1.2])
                    cols[0].markdown(
                        f"**{row['company_name_raw']}**\n\n<span style='font-family: JetBrains Mono; color: #64748B; font-size: 0.75rem;'>CIN: {row['cin']} | STATUS: {row['company_status']}</span>",
                        unsafe_allow_html=True,
                    )
                    has_cluster = pd.notna(row["cluster_id"])
                    cols[1].markdown(
                        f"<span style='font-family: JetBrains Mono; font-size: 0.8rem; color: #38BDF8;'>CLUSTER #{int(row['cluster_id'])}</span>"
                        if has_cluster
                        else "<span style='color: #475569; font-size: 0.8rem;'>NOT IN ANY GROUP</span>",
                        unsafe_allow_html=True,
                    )

                    if has_cluster and pd.notna(row["composite_score"]):
                        score = row["composite_score"]
                        flag_cat = row["flag_category"]
                        tag_class = (
                            "tag-high"
                            if flag_cat == "high_priority"
                            else "tag-mod" if flag_cat == "moderate" else "tag-base"
                        )
                        cols[2].markdown(
                            f"<span class='{tag_class}'>{score:.1f} • {FLAG_LABELS.get(flag_cat, flag_cat)}</span>",
                            unsafe_allow_html=True,
                        )
                    else:
                        cols[2].write("—")

                    if has_cluster:
                        cols[3].button(
                            "Inspect",
                            key=f"view_{int(row['entity_id'])}",
                            on_click=go,
                            args=("Cluster Detail",),
                            kwargs={"cluster": int(row["cluster_id"])},
                            use_container_width=True,
                        )
                st.markdown(
                    "<hr style='margin: 10px 0; border-color: #161F30;'>",
                    unsafe_allow_html=True,
                )

# ------------------------------------------------------ CLUSTER DETAIL
elif page == "Cluster Detail":
    st.markdown(
        """
        <div style="padding: 12px 0 16px 0;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #38BDF8; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px;">CLUSTER DETAIL</div>
            <h1 style="margin: 0; font-size: 1.8rem;">Cluster Detail</h1>
        </div>
    """,
        unsafe_allow_html=True,
    )
    st.write("A cluster is a group of companies that look alike. Open one from Search, or type a cluster number below.")

    auto_load = False
    if "selected_cluster" in st.session_state:
        st.session_state["cluster_input"] = st.session_state.pop("selected_cluster")
        auto_load = True

    c1, c2 = st.columns([3, 1])
    with c1:
        cluster_id = st.number_input("Cluster number", min_value=1, step=1, key="cluster_input")
    with c2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        load_clicked = st.button("Show cluster", use_container_width=True)

    if load_clicked or auto_load:
        data = load_cluster_view(int(cluster_id))
        scores = data["scores"]
        if not scores:
            st.error("No cluster found with that number. Use Search or the Leaderboard to find a valid one.")
        else:
            members = data["members"]
            flag = FLAG_LABELS.get(scores.get("flag_category"), scores.get("flag_category"))

            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Score", f"{scores['composite_score']:.1f} / 100")
            m2.metric("Classification", flag)
            m3.metric("Companies in Cluster", len(members))

            if scores.get("flag_category") == "high_priority":
                st.error("[HIGH PRIORITY] Several signals point the same way. This is a lead for human review, not a finding.")
            elif scores.get("flag_category") == "moderate":
                st.warning("[MODERATE] This group is somewhat unusual. Worth a look if time allows.")
            else:
                st.success("[BASELINE] This group is in the normal range.")

            if len(members) > 1 and members["address_raw"].nunique() == 1:
                st.info(f"All {len(members)} companies list the same registered address.")

            st.markdown("<h3 style='margin-top: 28px; font-size: 1.1rem;'>Why this was flagged</h3>", unsafe_allow_html=True)
            st.caption("Top 3 factors. A bigger number means that factor pushed the score up more.")
            ex = data["explanations"].copy()
            if not ex.empty:
                ex["Factor"] = ex["feature_name"].map(FEATURE_LABELS).fillna(ex["feature_name"])
                ex = ex.rename(columns={"shap_value": "Influence", "rank": "Rank"})
                st.dataframe(
                    ex[["Rank", "Factor", "Influence"]],
                    hide_index=True,
                    use_container_width=True,
                )

            st.markdown("<h3 style='margin-top: 28px; font-size: 1.1rem;'>Companies in this cluster</h3>", unsafe_allow_html=True)
            mem = members.rename(
                columns={
                    "entity_id": "Entity ID",
                    "company_name_raw": "Company Name",
                    "address_raw": "Registered Address",
                    "company_status": "Status",
                    "authorized_capital": "Authorized Capital",
                    "date_of_registration": "Registered On",
                }
            )
            st.dataframe(mem, hide_index=True, use_container_width=True)
    else:
        st.info("No cluster selected yet. Try an example:")
        for cid, label in EXAMPLE_CLUSTERS.items():
            st.button(
                label,
                key=f"cd_{cid}",
                on_click=go,
                args=("Cluster Detail",),
                kwargs={"cluster": cid},
            )

# --------------------------------------------------------- LEADERBOARD
elif page == "Leaderboard":
    st.markdown(
        """
        <div style="padding: 12px 0 16px 0;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #38BDF8; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px;">LEADERBOARD</div>
            <h1 style="margin: 0; font-size: 1.8rem;">Top Clusters by Score</h1>
        </div>
    """,
        unsafe_allow_html=True,
    )

    options = {
        "High Priority Only": "high_priority",
        "Moderate Only": "moderate",
        "Baseline Range Only": "baseline",
        "All Clusters": "all",
    }
    choice = st.selectbox("Show", list(options.keys()))

    data = get_leaderboard(flag=options[choice], limit=500)
    st.caption(
        f"Showing the top {len(data):,} clusters for this filter, highest score first. "
        "To open any other cluster, type its number in the box below."
    )

    shown = data.rename(
        columns={
            "cluster_id": "Cluster ID",
            "cluster_size": "Companies",
            "composite_score": "Score",
            "flag_category": "Classification",
        }
    )
    shown["Classification"] = shown["Classification"].map(FLAG_LABELS).fillna(shown["Classification"])
    st.dataframe(shown, hide_index=True, use_container_width=True)

    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        typed_id = st.number_input("Open any cluster by number", min_value=1, step=1, key="lb_typed")
    with col2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        st.button(
            "Inspect Cluster",
            on_click=go,
            args=("Cluster Detail",),
            kwargs={"cluster": int(typed_id)},
            use_container_width=True,
        )