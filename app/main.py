import pandas as pd
import streamlit as st
from queries import get_leaderboard, get_summary, load_cluster_view, search_company

# Page Configuration
st.set_page_config(
    page_title="ROC Pune | Corporate Registry Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Boutique Enterprise Dark-Mode Styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global Base */
    .main, .stApp {
        background-color: #07090E !important;
        font-family: 'Inter', sans-serif;
        color: #E2E8F0;
    }

    /* Hide Streamlit Default Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Sidebar Styling */
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

    /* Typography */
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

    /* Custom Metric Tickers */
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

    /* Action Buttons */
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

    /* Primary Submit Buttons */
    .stFormSubmitButton>button {
        background-color: #0284C7 !important;
        color: #FFFFFF !important;
        border: 1px solid #0284C7 !important;
        font-weight: 600 !important;
    }
    .stFormSubmitButton>button:hover {
        background-color: #0369A1 !important;
    }

    /* Enterprise Status Tags */
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

    /* Dataframe Matrix Grid */
    div[data-testid="stDataFrame"] {
        border: 1px solid #1B2A4A;
        border-radius: 6px;
        background-color: #0D131F;
    }

    /* Inputs */
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
    "moderate": "Moderate Risk",
    "baseline": "Baseline Range",
}
FEATURE_LABELS = {
    "address_signal_score": "Shared / Identical Addresses",
    "name_signal_score": "Phonetic Name Similarity",
    "timing_signal_score": "Synchronized Incorporation",
    "capital_similarity_score": "Authorized Capital Match",
    "topology_score": "Network Density Cluster",
    "category_homogeneity_score": "Industrial Homogeneity",
}
EXAMPLE_SEARCHES = ["nidhi", "cotton industry", "enterprises"]
EXAMPLE_CLUSTERS = {
    804: "Cluster #804 (Moderate Risk • Shared Address)",
    806: "Cluster #806 (High Priority • Score 100.0)",
}


def go(page_name, cluster=None, query=None):
    if cluster is not None:
        st.session_state["selected_cluster"] = int(cluster)
    if query is not None:
        st.session_state["search_query"] = query
    st.session_state["nav_override"] = page_name


if "nav_override" in st.session_state:
    st.session_state["page"] = st.session_state.pop("nav_override")

# Sidebar Command Nav
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

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="color: #64748B; font-size: 0.72rem; line-height: 1.5; font-family: 'JetBrains Mono', monospace;">
        <span style="color: #FBBF24;">[NOTICE]</span> Automated risk leads for investigative review. Not legal non-compliance findings.
    </div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- HOME
if page == "Home":
    st.markdown(
        """
        <div style="padding: 12px 0 24px 0;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #38BDF8; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 6px;">SYSTEM OVERVIEW // ACTIVE MATRIX</div>
            <h1 style="margin: 0; font-size: 2rem;">Corporate Registry Anomaly Intelligence</h1>
            <p style="color: #94A3B8; font-size: 0.95rem; max-width: 800px; margin-top: 8px; line-height: 1.6;">
                Unsupervised network clustering and Isolation Forest anomaly attribution designed to isolate synthetic shell entity clusters,
                synchronized incorporations, and complex registry topologies across ROC Pune datasets.
            </p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    try:
        s = get_summary()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Entities Audited", f"{s['companies']:,}")
        c2.metric("Network Clusters", f"{s['clusters']:,}")
        c3.metric("High Priority Flags", f"{s['high']:,}")
        c4.metric("Moderate Risk Flags", f"{s['moderate']:,}")
    except Exception:
        st.caption("Live aggregate metrics offline.")

    st.markdown(
        "<h3 style='margin-top: 36px; font-size: 1.1rem; font-family: 'JetBrains Mono', monospace; color: #64748B;'>ANALYTICAL WORKFLOW</h3>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            "<div style='background: #0D131F; border: 1px solid #1B2A4A; border-radius: 6px; padding: 18px; height: 100%;'>"
            "<div style='font-family: JetBrains Mono; font-size: 0.75rem; color: #38BDF8;'>01 / SEARCH</div>"
            "<div style='font-weight: 600; margin-top: 8px; margin-bottom: 6px;'>Entity Screening</div>"
            "<div style='color: #94A3B8; font-size: 0.85rem;'>Query normalized entity records, CIN codes, and baseline structural properties.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            "<div style='background: #0D131F; border: 1px solid #1B2A4A; border-radius: 6px; padding: 18px; height: 100%;'>"
            "<div style='font-family: JetBrains Mono; font-size: 0.75rem; color: #38BDF8;'>02 / INSPECT</div>"
            "<div style='font-weight: 600; margin-top: 8px; margin-bottom: 6px;'>Cluster Graph Analysis</div>"
            "<div style='color: #94A3B8; font-size: 0.85rem;'>Isolate multi-entity networks to evaluate address convergence and SHAP attribution vectors.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            "<div style='background: #0D131F; border: 1px solid #1B2A4A; border-radius: 6px; padding: 18px; height: 100%;'>"
            "<div style='font-family: JetBrains Mono; font-size: 0.75rem; color: #38BDF8;'>03 / PRIORITIZE</div>"
            "<div style='font-weight: 600; margin-top: 8px; margin-bottom: 6px;'>Risk Leaderboard</div>"
            "<div style='color: #94A3B8; font-size: 0.85rem;'>Review sorted inventories of high-priority anomalies ordered by statistical severity.</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<h3 style='margin-top: 36px; font-size: 1.1rem; font-family: 'JetBrains Mono', monospace; color: #64748B;'>QUICK ACCESS PRESETS</h3>",
        unsafe_allow_html=True,
    )
    a, b = st.columns(2)
    with a:
        st.markdown("<div style='font-size: 0.85rem; color: #94A3B8; margin-bottom: 8px;'>Preset Entity Queries</div>", unsafe_allow_html=True)
        for term in EXAMPLE_SEARCHES:
            st.button(
                f"Query: '{term}'",
                key=f"home_s_{term}",
                on_click=go,
                args=("Search",),
                kwargs={"query": term},
                use_container_width=True,
            )
    with b:
        st.markdown("<div style='font-size: 0.85rem; color: #94A3B8; margin-bottom: 8px;'>Verified Case Studies</div>", unsafe_allow_html=True)
        for cid, label in EXAMPLE_CLUSTERS.items():
            st.button(
                f"Load {label}",
                key=f"home_c_{cid}",
                on_click=go,
                args=("Cluster Detail",),
                kwargs={"cluster": cid},
                use_container_width=True,
            )

# -------------------------------------------------------------- SEARCH
elif page == "Search":
    st.markdown(
        """
        <div style="padding: 12px 0 16px 0;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #38BDF8; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px;">DATABASE SEARCH // INDEX</div>
            <h1 style="margin: 0; font-size: 1.8rem;">Entity Screening Matrix</h1>
        </div>
    """,
        unsafe_allow_html=True,
    )

    with st.form("search_form"):
        col1, col2 = st.columns([5, 1])
        with col1:
            typed = st.text_input(
                "Search Term",
                value=st.session_state.get("search_query", ""),
                placeholder="Enter company keyword or 21-digit CIN...",
                label_visibility="collapsed",
            )
        with col2:
            submitted = st.form_submit_button(
                "Execute", use_container_width=True
            )

    if submitted:
        st.session_state["search_query"] = typed.strip()

    query = st.session_state.get("search_query", "")
    if not query:
        st.markdown("<div style='color: #64748B; font-size: 0.85rem; margin-top: 16px;'>Select a preset search query to initialize screening:</div>", unsafe_allow_html=True)
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
        st.warning("Query string must contain at least 3 characters.")
    else:
        results = search_company(query)
        if results.empty:
            st.warning(f"No records matching query: '{query}'")
        else:
            st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 0.75rem; color: #64748B; margin-bottom: 12px;'>MATCHES FOUND: {len(results)} (PRIORITIZED BY CLUSTER ASSOCIATION)</div>", unsafe_allow_html=True)
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
                        else "<span style='color: #475569; font-size: 0.8rem;'>UNCLUSTERED</span>",
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
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #38BDF8; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px;">TOPOLOGY INSPECTOR // DEEP DIVE</div>
            <h1 style="margin: 0; font-size: 1.8rem;">Cluster Dependency Matrix</h1>
        </div>
    """,
        unsafe_allow_html=True,
    )

    auto_load = False
    if "selected_cluster" in st.session_state:
        st.session_state["cluster_input"] = st.session_state.pop(
            "selected_cluster"
        )
        auto_load = True

    c1, c2 = st.columns([3, 1])
    with c1:
        cluster_id = st.number_input(
            "Cluster ID Reference", min_value=1, step=1, key="cluster_input"
        )
    with c2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        load_clicked = st.button("Load Matrix", use_container_width=True)

    if load_clicked or auto_load:
        data = load_cluster_view(int(cluster_id))
        scores = data["scores"]
        if not scores:
            st.error("Cluster reference not found in database.")
        else:
            members = data["members"]
            flag = FLAG_LABELS.get(
                scores.get("flag_category"), scores.get("flag_category")
            )

            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Composite Risk Score", f"{scores['composite_score']:.1f} / 100")
            m2.metric("Classification", flag)
            m3.metric("Associated Entities", len(members))

            if scores.get("flag_category") == "high_priority":
                st.error("[CRITICAL ANOMALY] Multi-signal convergence detected across structural dimensions.")
            elif scores.get("flag_category") == "moderate":
                st.warning("[MODERATE RISK] Notable correlation across structural attribute vectors.")
            else:
                st.success("[BASELINE] Entity configuration falls within normal statistical parameters.")

            if len(members) > 1 and members["address_raw"].nunique() == 1:
                st.info("[INFRASTRUCTURE ALERT] All cluster members list an identical registered address string.")

            st.markdown("<h3 style='margin-top: 28px; font-size: 1.1rem; font-family: 'JetBrains Mono', monospace;'>SHAP Attribution Vectors</h3>", unsafe_allow_html=True)
            ex = data["explanations"].copy()
            if not ex.empty:
                ex["Indicator Factor"] = (
                    ex["feature_name"]
                    .map(FEATURE_LABELS)
                    .fillna(ex["feature_name"])
                )
                ex = ex.rename(
                    columns={"shap_value": "Attribution Impact", "rank": "Rank"}
                )
                st.dataframe(
                    ex[["Rank", "Indicator Factor", "Attribution Impact"]],
                    hide_index=True,
                    use_container_width=True,
                )

            st.markdown("<h3 style='margin-top: 28px; font-size: 1.1rem; font-family: 'JetBrains Mono', monospace;'>Cluster Member Registry</h3>", unsafe_allow_html=True)
            mem = members.rename(
                columns={
                    "entity_id": "Entity ID",
                    "company_name_raw": "Company Name",
                    "address_raw": "Registered Address",
                    "company_status": "Status",
                    "authorized_capital": "Capital",
                    "date_of_registration": "Registration Date",
                }
            )
            st.dataframe(mem, hide_index=True, use_container_width=True)

# --------------------------------------------------------- LEADERBOARD
elif page == "Leaderboard":
    st.markdown(
        """
        <div style="padding: 12px 0 16px 0;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #38BDF8; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px;">RISK RANKINGS // LEADERBOARD</div>
            <h1 style="margin: 0; font-size: 1.8rem;">High Anomaly Priority Index</h1>
        </div>
    """,
        unsafe_allow_html=True,
    )

    options = {
        "High Priority Only": "high_priority",
        "Moderate Risk Only": "moderate",
        "Baseline Range Only": "baseline",
        "All Flagged Clusters": "all",
    }
    choice = st.selectbox("Filter Risk Classification", list(options.keys()))

    data = get_leaderboard(limit=500)
    if options[choice] != "all":
        data = data[data["flag_category"] == options[choice]]

    shown = data.rename(
        columns={
            "cluster_id": "Cluster ID",
            "cluster_size": "Member Count",
            "composite_score": "Composite Score",
            "flag_category": "Classification",
        }
    )
    shown["Classification"] = shown["Classification"].map(
        FLAG_LABELS
    ).fillna(shown["Classification"])

    st.dataframe(shown, hide_index=True, use_container_width=True)

    if not data.empty:
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            pick = st.selectbox("Select Cluster ID for Direct Inspection", data["cluster_id"].tolist())
        with col2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            st.button(
                "Inspect Cluster",
                on_click=go,
                args=("Cluster Detail",),
                kwargs={"cluster": int(pick)},
                use_container_width=True,
            )
