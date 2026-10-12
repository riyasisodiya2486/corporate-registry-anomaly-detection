import pandas as pd
import streamlit as st
from queries import get_leaderboard, get_summary, load_cluster_view, search_company

# Page Configuration
st.set_page_config(
    page_title="Corporate Registry Intelligence Platform",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Professional Dark Mode Enterprise CSS & SVG Icon Library
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global Typography & Background */
    .main, .stApp {
        background-color: #0B0F19 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #F8FAFC;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid #1E293B;
    }
    section[data-testid="stSidebar"] .stRadio label {
        color: #94A3B8 !important;
        font-weight: 500;
    }
    section[data-testid="stSidebar"] .stRadio label:hover {
        color: #F8FAFC !important;
    }

    /* Headings */
    h1, h2, h3 {
        color: #F8FAFC !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }

    /* Enterprise Metric Cards */
    div[data-testid="stMetric"] {
        background: #111827;
        border: 1px solid #1F2937;
        border-radius: 10px;
        padding: 22px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    div[data-testid="stMetricLabel"] {
        color: #9CA3AF !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #F8FAFC !important;
        font-size: 1.9rem !important;
        font-weight: 700 !important;
    }

    /* Buttons */
    .stButton>button {
        background-color: #111827 !important;
        color: #E2E8F0 !important;
        border: 1px solid #374151 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.55rem 1.1rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        background-color: #1F2937 !important;
        border-color: #4B5563 !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.15);
    }

    /* Primary Action Buttons */
    button[kind="primary"], .stFormSubmitButton>button {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: 1px solid #2563EB !important;
    }
    button[kind="primary"]:hover, .stFormSubmitButton>button:hover {
        background-color: #1D4ED8 !important;
    }

    /* Risk Badges */
    .badge-high {
        background-color: rgba(153, 27, 27, 0.25);
        color: #FCA5A5;
        border: 1px solid rgba(248, 113, 113, 0.4);
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-mod {
        background-color: rgba(180, 83, 9, 0.25);
        color: #FCD34D;
        border: 1px solid rgba(251, 191, 36, 0.4);
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-base {
        background-color: rgba(6, 95, 70, 0.25);
        color: #6EE7B7;
        border: 1px solid rgba(52, 211, 153, 0.4);
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Dataframe Containers */
    div[data-testid="stDataFrame"] {
        border: 1px solid #1F2937;
        border-radius: 10px;
        background-color: #111827;
        overflow: hidden;
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
    "address_signal_score": "Shared / Identical Registered Addresses",
    "name_signal_score": "Phonetic / Structural Name Similarity",
    "timing_signal_score": "Synchronized Incorporation Dates",
    "capital_similarity_score": "Authorized Capital Alignment",
    "topology_score": "Network Connectivity Density",
    "category_homogeneity_score": "Industrial Classification Homogeneity",
}
EXAMPLE_SEARCHES = ["nidhi", "cotton industry", "enterprises"]
EXAMPLE_CLUSTERS = {
    804: "Cluster #804 (Moderate Risk • Shared Address)",
    806: "Cluster #806 (High Priority • Composite 100.0)",
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
    <div style="padding: 12px 0 20px 0; border-bottom: 1px solid #1E293B; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            <h3 style="color: #F8FAFC; margin: 0; font-size: 1.05rem; font-weight: 600;">ROC Intelligence</h3>
        </div>
        <p style="color: #64748B; font-size: 0.75rem; margin: 6px 0 0 34px; text-transform: uppercase; letter-spacing: 0.05em;">Enterprise AML & Audit</p>
    </div>
""",
    unsafe_allow_html=True,
)

page = st.sidebar.radio("Navigation", PAGES, key="page")

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="color: #64748B; font-size: 0.75rem; line-height: 1.5; padding: 4px 0;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 4px;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <strong>Regulatory Notice:</strong><br>
        Flags denote automated risk leads for auditor review and do not constitute formal non-compliance findings.
    </div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- HOME
if page == "Home":
    st.markdown(
        """
        <div style="padding: 8px 0 16px 0;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <h1 style="margin: 0; font-size: 2rem;">Corporate Registry Anomaly Intelligence</h1>
            </div>
            <p style="color: #94A3B8; font-size: 1.05rem; max-width: 850px; line-height: 1.5;">
                Advanced graph topology analysis and unsupervised machine learning models engineered to uncover 
                synthetic shell entity networks, synchronized formations, and complex structural overlaps across regional corporate registers.
            </p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    try:
        s = get_summary()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Entities Audited", f"{s['companies']:,}")
        c2.metric("Discovered Networks", f"{s['clusters']:,}")
        c3.metric("High Priority Flags", f"{s['high']:,}")
        c4.metric("Moderate Risk Flags", f"{s['moderate']:,}")
    except Exception:
        st.caption("Live aggregate metrics temporarily unavailable.")

    st.markdown(
        "<h3 style='margin-top: 32px; font-size: 1.25rem;'>Operational Architecture</h3>",
        unsafe_allow_html=True,
    )
    col_step1, col_step2, col_step3 = st.columns(3)
    with col_step1:
        st.markdown(
            "**1. Entity Indexing & Screening**\n\nQuery parsed entity vectors, normalized strings, and baseline features by name or CIN."
        )
    with col_step2:
        st.markdown(
            "**2. Multi-Signal Clustering**\n\nIsolate entity clusters evaluated through address matches, temporal proximity, and capitalization alignment."
        )
    with col_step3:
        st.markdown(
            "**3. Explainable Risk Scoring**\n\nExamine Isolation Forest anomaly scores supported by SHAP feature attribution weights."
        )

    st.markdown("---")
    st.markdown(
        "<h3 style='font-size: 1.25rem;'>Quick Navigation & Presets</h3>",
        unsafe_allow_html=True,
    )
    a, b = st.columns(2)
    with a:
        st.markdown(
            "<span style='color: #94A3B8; font-size: 0.9rem; font-weight: 600;'>RECOMMENDED SEARCHES</span>",
            unsafe_allow_html=True,
        )
        for term in EXAMPLE_SEARCHES:
            st.button(
                f"Query registry for '{term}'",
                key=f"home_s_{term}",
                on_click=go,
                args=("Search",),
                kwargs={"query": term},
                use_container_width=True,
            )
    with b:
        st.markdown(
            "<span style='color: #94A3B8; font-size: 0.9rem; font-weight: 600;'>VERIFIED CASE STUDIES</span>",
            unsafe_allow_html=True,
        )
        for cid, label in EXAMPLE_CLUSTERS.items():
            st.button(
                f"Inspect {label}",
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
        <div>
            <h1 style="font-size: 1.8rem; margin-bottom: 4px;">Entity Lookup & Screening</h1>
            <p style="color: #94A3B8; font-size: 0.95rem;">Query indexed records with automated cluster association ranking.</p>
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
                placeholder="Enter company name keyword or 21-digit CIN...",
                label_visibility="collapsed",
            )
        with col2:
            submitted = st.form_submit_button(
                "Search", use_container_width=True
            )

    if submitted:
        st.session_state["search_query"] = typed.strip()

    query = st.session_state.get("search_query", "")
    if not query:
        st.markdown(
            "<p style='color: #94A3B8; margin-top: 16px;'>Select a preset search query to examine results:</p>",
            unsafe_allow_html=True,
        )
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
        st.warning("Please enter a minimum of 3 characters for query execution.")
    else:
        results = search_company(query)
        if results.empty:
            st.warning(f"No matching registry records found for '{query}'.")
        else:
            st.markdown(
                f"<p style='color: #94A3B8; font-size: 0.85rem;'>Displaying top {len(results)} matches. Clustered entities are prioritized.</p>",
                unsafe_allow_html=True,
            )
            for _, row in results.iterrows():
                with st.container():
                    cols = st.columns([4, 2, 2, 1.5])
                    cols[0].markdown(
                        f"**{row['company_name_raw']}**\n\n<span style='color: #94A3B8; font-size: 0.8rem;'>CIN: {row['cin']} &nbsp;|&nbsp; Status: {row['company_status']}</span>",
                        unsafe_allow_html=True,
                    )
                    has_cluster = pd.notna(row["cluster_id"])
                    cols[1].markdown(
                        f"**Cluster #{int(row['cluster_id'])}**"
                        if has_cluster
                        else "<span style='color: #64748B;'>Unclustered</span>",
                        unsafe_allow_html=True,
                    )

                    if has_cluster and pd.notna(row["composite_score"]):
                        score = row["composite_score"]
                        flag_cat = row["flag_category"]
                        badge_class = (
                            "badge-high"
                            if flag_cat == "high_priority"
                            else "badge-mod" if flag_cat == "moderate" else "badge-base"
                        )
                        cols[2].markdown(
                            f"<span class='{badge_class}'>{score:.1f} • {FLAG_LABELS.get(flag_cat, flag_cat)}</span>",
                            unsafe_allow_html=True,
                        )
                    else:
                        cols[2].write("—")

                    if has_cluster:
                        cols[3].button(
                            "View Details",
                            key=f"view_{int(row['entity_id'])}",
                            on_click=go,
                            args=("Cluster Detail",),
                            kwargs={"cluster": int(row["cluster_id"])},
                            use_container_width=True,
                        )
                st.markdown(
                    "<hr style='margin: 12px 0; border-color: #1F2937;'>",
                    unsafe_allow_html=True,
                )

# ------------------------------------------------------ CLUSTER DETAIL
elif page == "Cluster Detail":
    st.markdown(
        """
        <div>
            <h1 style="font-size: 1.8rem; margin-bottom: 4px;">Cluster Dependency Inspector</h1>
            <p style="color: #94A3B8; font-size: 0.95rem;">Examine structural properties, member entities, and attribution vectors.</p>
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
            "Cluster ID Number", min_value=1, step=1, key="cluster_input"
        )
    with c2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        load_clicked = st.button("Load Cluster", use_container_width=True)

    if load_clicked or auto_load:
        data = load_cluster_view(int(cluster_id))
        scores = data["scores"]
        if not scores:
            st.error("No cluster record found matching the specified ID.")
        else:
            members = data["members"]
            flag = FLAG_LABELS.get(
                scores.get("flag_category"), scores.get("flag_category")
            )

            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Composite Risk Score", f"{scores['composite_score']:.1f} / 100")
            m2.metric("Risk Classification", flag)
            m3.metric("Cluster Member Count", len(members))

            if scores.get("flag_category") == "high_priority":
                st.error("High Priority Anomaly: Multiple converging indicators suggest high structural risk.")
            elif scores.get("flag_category") == "moderate":
                st.warning("Moderate Risk: Notable correlation across several registry attributes.")
            else:
                st.success("Baseline Classification: Group attributes fall within normal statistical limits.")

            if len(members) > 1 and members["address_raw"].nunique() == 1:
                st.info("Address Convergence Notice: All member entities share an identical registered address string.")

            st.markdown(
                "<h3 style='margin-top: 24px; font-size: 1.2rem;'>Anomaly Attribution Analysis (SHAP)</h3>",
                unsafe_allow_html=True,
            )
            st.caption("Quantifies the marginal impact of each signal feature on the overall composite score.")
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

            st.markdown(
                "<h3 style='margin-top: 24px; font-size: 1.2rem;'>Member Entities Registry</h3>",
                unsafe_allow_html=True,
            )
            mem = members.rename(
                columns={
                    "entity_id": "Entity ID",
                    "company_name_raw": "Company Name",
                    "address_raw": "Registered Address",
                    "company_status": "Status",
                    "authorized_capital": "Authorized Capital",
                    "date_of_registration": "Registration Date",
                }
            )
            st.dataframe(mem, hide_index=True, use_container_width=True)

# --------------------------------------------------------- LEADERBOARD
elif page == "Leaderboard":
    st.markdown(
        """
        <div>
            <h1 style="font-size: 1.8rem; margin-bottom: 4px;">Risk Leaderboard</h1>
            <p style="color: #94A3B8; font-size: 0.95rem;">Ranked inventory of corporate clusters ordered by descending composite anomaly scores.</p>
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
    choice = st.selectbox("Filter Risk Category", list(options.keys()))

    data = get_leaderboard(limit=500)
    if options[choice] != "all":
        data = data[data["flag_category"] == options[choice]]

    shown = data.rename(
        columns={
            "cluster_id": "Cluster ID",
            "cluster_size": "Member Count",
            "composite_score": "Composite Score",
            "flag_category": "Risk Classification",
        }
    )
    shown["Risk Classification"] = shown["Risk Classification"].map(
        FLAG_LABELS
    ).fillna(shown["Risk Classification"])

    st.dataframe(shown, hide_index=True, use_container_width=True)

    if not data.empty:
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            pick = st.selectbox("Select Cluster ID for Inspection", data["cluster_id"].tolist())
        with col2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            st.button(
                "Open Cluster",
                on_click=go,
                args=("Cluster Detail",),
                kwargs={"cluster": int(pick)},
                use_container_width=True,
            )