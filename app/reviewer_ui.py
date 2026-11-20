import hmac
import os
import re

import streamlit as st

from queries import (BLIND_MODE, CHECK_COLUMNS, OPEN_MODE, VERDICTS, get_reviews,
                     load_cluster_extras, load_cluster_view, next_queue_cluster,
                     reviewer_enabled, reviewer_passcode, reviewer_progress, save_review)

QUEUE_BATCH = os.environ.get("REVIEW_BATCH", "r1")   # set REVIEW_BATCH=r2 for Round 2
OPEN_ROUND = "open"
MAX_FAILS = 5

# ASSUMPTION: these answer options are guesses. Replace them with the allowed values from
# show_constraints.py / your v1 audit view, so v1 and v2 labels are comparable.
CHECK_QUESTIONS = {
    "duplicate_record": ("Do the records look like the same company entered more than once?",
                         ["yes", "no", "unsure"]),
    "address_type": ("What kind of registered address is it?",
                     ["residential", "commercial", "placeholder", "unclear"]),
    "registered_close": ("Were the members registered close together in time?",
                         ["yes", "no", "unsure"]),
    "directors_shared": ("Are directors shared? (not visible here, so usually 'unknown')",
                         ["yes", "no", "unknown"]),
    "filings_ok": ("Do the filings look normal? (not visible here, so usually 'unknown')",
                   ["yes", "no", "unknown"]),
    "office_exists": ("Does a real office exist? (needs outside information, so usually 'unknown')",
                      ["yes", "no", "unknown"]),
}
VERDICT_LABELS = {
    "worth_review": "worth_review: a human investigator should look at this",
    "ordinary": "ordinary: looks like normal, unrelated or harmless companies",
    "data_artifact": "data_artifact: duplicate or placeholder data, not a real pattern",
    "need_more_info": "need_more_info: cannot decide from what is shown",
}


def render_reviewer_login():
    """Sidebar login. Does nothing if REVIEWER_* values are not configured."""
    if not reviewer_enabled():
        return
    ss = st.session_state
    with st.sidebar.expander("Reviewer login", expanded=not ss.get("reviewer_ok", False)):
        st.caption("Reviewers: sign in here to start your queue.")
        if ss.get("reviewer_ok"):
            st.write(f"Signed in as **{ss['reviewer_name']}**")
            if st.button("Sign out", key="rev_signout"):
                for k in ("reviewer_ok", "reviewer_name", "leave_blind"):
                    ss.pop(k, None)
                st.rerun()
            return
        name = st.text_input("Your name (letters only)", key="rev_name_input")
        code = st.text_input("Passcode", type="password", key="rev_code_input")
        if st.button("Sign in", key="rev_signin"):
            clean = re.sub(r"[^a-z0-9]", "", name.strip().lower())
            if ss.get("login_fails", 0) >= MAX_FAILS:
                st.error("Too many wrong attempts. Reload the page to try again.")
            elif not clean:
                st.error("Enter your name.")
            elif hmac.compare_digest(code.encode("utf-8"), reviewer_passcode().encode("utf-8")):
                ss["reviewer_ok"] = True
                ss["reviewer_name"] = clean
                ss["login_fails"] = 0
                ss["nav_override"] = "Cluster Detail"   # go straight to the review screen
                st.rerun()
            else:
                ss["login_fails"] = ss.get("login_fails", 0) + 1
                st.error("Wrong passcode.")


def blind_active() -> bool:
    """True while a signed-in reviewer must stay blind: until their queue is finished, and
    afterwards until they tick 'Leave blind mode'. Blind mode hides scores, flags, SHAP and status.
    This is a procedural control, not a security boundary."""
    ss = st.session_state
    if not ss.get("reviewer_ok"):
        return False
    try:
        done, total = reviewer_progress(QUEUE_BATCH, ss["reviewer_name"])
    except Exception:
        return True   # on error, stay blind
    if total and done < total:
        return True
    return not ss.get("leave_blind", False)


def _form(review_round: str, mode: str, cluster_id: int, reviewer: str, key: str) -> bool:
    """Review form. Returns True after a successful save."""
    with st.form(key):
        st.markdown("**Structured checks** (answer all six)")
        answers = {}
        for col in CHECK_COLUMNS:
            question, options = CHECK_QUESTIONS[col]
            default = options.index("unknown") if "unknown" in options else None
            answers[col] = st.radio(question, options, index=default, horizontal=True,
                                    key=f"{key}_{col}")
        verdict = st.radio("Verdict (required)", VERDICTS, index=None,
                           format_func=lambda v: VERDICT_LABELS[v], key=f"{key}_verdict")
        note = st.text_area("Optional note (max 500 characters)", max_chars=500, key=f"{key}_note")
        st.caption("Do not write any person's name (for example a director) in the note.")
        submitted = st.form_submit_button("Save review")
    if not submitted:
        return False
    if verdict is None or any(v is None for v in answers.values()):
        st.error("Answer all six checks and pick a verdict before saving.")
        return False
    try:
        save_review(review_round, mode, cluster_id, reviewer, answers, verdict, note)
    except Exception as e:
        first = (str(e).splitlines() or [""])[0][:200]
        st.session_state["save_error"] = f"{type(e).__name__}: {first}"
        st.rerun()
    st.session_state["save_ok"] = True
    return True


def render_blind_queue():
    """Blind review screen. Members only: no score, flag, SHAP or status."""
    ss = st.session_state
    if not ss.get("reviewer_ok"):
        st.info("Blind review: sign in with the Reviewer login in the sidebar.")
        return
    reviewer = ss["reviewer_name"]
    if ss.pop("save_ok", False):
        st.success("Review saved. Here is the next group.")
    if ss.get("save_error"):
        st.error(f"Could not save: {ss.pop('save_error')}")
    done, total = reviewer_progress(QUEUE_BATCH, reviewer)
    st.progress(min(done / total, 1.0) if total else 0.0,
                text=f"Batch {QUEUE_BATCH}: {done} of {total} reviewed")
    with st.expander("How to review (read once)", expanded=(done == 0)):
        st.markdown(
            "**What you decide:** is this group worth a human investigator's time? "
            "You are not deciding that anyone did something wrong.\n\n"
            "1. Read the companies table and the address table below.\n"
            "2. Answer the six checks. The last three default to *unknown* because that "
            "information is not shown here. Do not guess them.\n"
            "3. Pick one verdict:\n"
            "   - **data_artifact**: duplicate records or a placeholder address\n"
            "   - **worth_review**: real signs point the same way with no harmless explanation\n"
            "   - **ordinary**: a harmless explanation, or only a generic word in common\n"
            "   - **need_more_info**: cannot decide from what is shown\n"
            "4. Press *Save review*. The next group appears automatically.\n\n"
            "Work alone. Do not look anyone up. Do not write personal names in notes."
        )
    if total == 0:
        st.warning(f"No clusters queued for batch {QUEUE_BATCH}.")
        return
    if done >= total:
        st.success("Your queue is complete. Thank you.")
        st.markdown("#### All reviews in this batch")
        st.caption("Visible only because you finished. Do not discuss before everyone is done.")
        st.dataframe(get_reviews(QUEUE_BATCH), hide_index=True, use_container_width=True)
        st.checkbox("Leave blind mode (shows scores and flags; do not review more in this batch)",
                    key="leave_blind")
        return

    cid = next_queue_cluster(QUEUE_BATCH, reviewer)
    if cid is None:
        return
    members = load_cluster_view(cid)["members"][
        ["entity_id", "company_name_raw", "address_raw", "authorized_capital", "date_of_registration"]]
    st.markdown(f"### Item {done + 1} of {total} (cluster #{cid})")
    st.caption("Judge only from what is shown. Scores, flags and status are hidden on purpose.")
    st.dataframe(members.rename(columns={
        "entity_id": "Entity ID", "company_name_raw": "Company Name",
        "address_raw": "Registered Address", "authorized_capital": "Authorized Capital",
        "date_of_registration": "Registered On"}), hide_index=True, use_container_width=True)

    reuse = load_cluster_extras(cid)["reuse"]
    if not reuse.empty:
        st.caption("How many clusters each address in this group appears in:")
        st.dataframe(reuse.rename(columns={"address_normalized": "Address (normalised)",
                                           "n_clusters": "Clusters using it"}),
                     hide_index=True, use_container_width=True)

    if _form(QUEUE_BATCH, BLIND_MODE, cid, reviewer, f"blind_{QUEUE_BATCH}_{cid}_{reviewer}"):
        st.rerun()


def render_open_review(cluster_id: int):
    """Optional review of any cluster, shown in normal mode. Stored as mode 'open'."""
    ss = st.session_state
    if not reviewer_enabled() or not ss.get("reviewer_ok"):
        return
    with st.expander("Add an open review of this cluster"):
        st.caption("Open reviews are stored with mode 'open'. You have seen the score, so they "
                   "are NOT blind labels and must never be used for evaluation.")
        if _form(OPEN_ROUND, OPEN_MODE, int(cluster_id), ss["reviewer_name"],
                 f"open_{cluster_id}_{ss['reviewer_name']}"):
            st.success("Saved.")