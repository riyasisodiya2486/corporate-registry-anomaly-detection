Riya. Three small edits to app/main.py for the network view and dossier. Needs: pip install pyvis (add `pyvis` to requirements.txt).

EDIT 1 (imports at the top): add `import streamlit.components.v1 as components` and
    from v2_views import build_dossier, network_fig, network_html
and add `load_cluster_extras` to the `from queries import (...)` list.

EDIT 2 (Cluster Detail, directly after the line that shows the members table
`st.dataframe(mem, hide_index=True, use_container_width=True)`; same indentation as that line):

            extras = load_cluster_extras(int(cluster_id))
            st.markdown("<h3 style='margin-top: 28px; font-size: 1.1rem;'>Company network</h3>", unsafe_allow_html=True)
            st.caption("Links: same address, same name stem, registered within 30 days. Red = struck off, green = other.")
            html = network_html(extras["members"])
            if html:
                components.html(html, height=440, scrolling=False)
            else:
                st.pyplot(network_fig(extras["members"]))

            facts, dossier_text = build_dossier(int(cluster_id), scores, extras["members"], data["explanations"],
                                                extras["reuse"], FEATURE_LABELS)
            st.markdown("<h3 style='margin-top: 28px; font-size: 1.1rem;'>Evidence dossier</h3>", unsafe_allow_html=True)
            for fact in facts:
                st.write("- " + fact)
            st.caption("This is a lead for human review, not a finding of wrongdoing.")
            st.download_button("Download dossier (text)", dossier_text, file_name=f"dossier_cluster_{int(cluster_id)}.txt")

EDIT 3: no other change. The dossier never shows director names; the app shows counts and facts only.
