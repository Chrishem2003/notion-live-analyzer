"""
🎓 Professor Vault — encrypted student submissions and marking.

Submissions are sealed with AES-256-GCM under a password the professor sets
for the project; the database never holds the key, so nothing here can be read
from a leaked file alone.
"""
import streamlit as st

st.set_page_config(page_title="Professor Vault", layout="wide", page_icon="🎓")

from modules.audit_portal import CHRISHEMSubmissionSystem  # noqa: E402
from modules.billing import PROFESSOR_SUITE  # noqa: E402
from modules.config import init_session_state  # noqa: E402
from modules.professor_vault import (  # noqa: E402
    VaultError,
    VaultLocked,
    check_password_strength,
)
from modules.session_auth import entitlement, render_account_badge  # noqa: E402
from modules.ui_components import load_css, section_header, watermark  # noqa: E402

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
watermark("CHRISHEM")

with st.sidebar:
    render_account_badge()

section_header("🎓 Professor Vault")
st.caption(
    "Students submit work encrypted end-to-end; only the project password opens it. "
    "Marks and feedback are sealed the same way."
)

system = CHRISHEMSubmissionSystem()
project_id = int(st.number_input("Project ID", min_value=0, value=0, step=1))

student_tab, professor_tab = st.tabs(["📤 Submit work", "🔍 Review submissions"])

# ─── Student side ─────────────────────────────────────────────────────
with student_tab:
    if not system.vault_password_set(project_id):
        st.info(
            "This project has no vault password yet — a professor must set one in "
            "the Review tab before submissions can be encrypted."
        )
    with st.form("submit_work"):
        name = st.text_input("Your name")
        email = st.text_input("Your email (optional)")
        title = st.text_input("Submission title")
        content = st.text_area("Paste your work", height=260)
        password = st.text_input(
            "Project vault password", type="password",
            help="Given to you by your supervisor. It is the only key to your submission.",
        )
        submitted = st.form_submit_button("🔒 Encrypt & submit", type="primary")

    if submitted:
        if not (name and title and content and password):
            st.error("Name, title, work and the vault password are all required.")
        elif not system.unlock(project_id, password):
            st.error("That vault password does not match this project.")
        else:
            try:
                result = system.submit(
                    project_id, name, title, content, password, student_email=email
                )
            except VaultError as exc:
                st.error(str(exc))
            else:
                st.success(result["message"])
                st.caption(f"Integrity hash: `{result['blockchain_hash'][:32]}…`")

# ─── Professor side ───────────────────────────────────────────────────
with professor_tab:
    access = entitlement(PROFESSOR_SUITE)
    if not access.allowed:
        st.warning(access.reason)
        st.page_link("pages/48_💳_Pricing.py", label="See plans", icon="💳")
        st.stop()

    if not system.vault_password_set(project_id):
        st.markdown("#### Set the vault password for this project")
        st.caption(
            "Choose it once and share it with your students. It cannot be recovered "
            "from the database — keep a copy."
        )
        with st.form("set_vault"):
            new_password = st.text_input("New vault password", type="password")
            confirm = st.text_input("Confirm", type="password")
            if st.form_submit_button("Set password", type="primary"):
                strength = check_password_strength(new_password)
                if not strength.ok:
                    st.error(strength.reason)
                elif new_password != confirm:
                    st.error("The two passwords do not match.")
                else:
                    system.set_vault_password(project_id, new_password)
                    st.success("Vault password set. Students can submit now.")
                    st.rerun()
        st.stop()

    password = st.text_input("Vault password", type="password", key="prof_password")
    if not password:
        st.info("Enter the project vault password to open submissions.")
        st.stop()
    if not system.unlock(project_id, password):
        st.error("❌ Incorrect password. Access denied.")
        st.stop()

    submissions = system.get_submissions(project_id=project_id)
    if not submissions:
        st.info("No submissions for this project yet.")
        st.stop()

    st.success(f"🔓 Vault open — {len(submissions)} submissions.")
    labels = {
        s["id"]: f"{s['student_name']} — {s['title']} ({s['status']})" for s in submissions
    }
    chosen = st.selectbox(
        "Submission", options=list(labels), format_func=lambda i: labels[i]
    )
    record = system.get_submission(chosen)

    try:
        plaintext = system.decrypt_submission(chosen, password)
    except VaultLocked as exc:
        st.error(f"❌ {exc}")
        st.stop()

    st.text_area("Submitted work", value=plaintext, height=320, disabled=True)
    stats = system.get_student_stats(project_id, record["student_name"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Submissions by this student", stats["total_submissions"])
    col2.metric("Reviewed", stats["reviewed"])
    col3.metric("Average score", stats["average_score"] or "—")

    st.markdown("#### Mark this submission")
    with st.form("review"):
        grade = st.text_input("Grade", value=record.get("professor_grade") or "")
        score = st.number_input("Score", min_value=0.0, max_value=100.0, value=0.0)
        feedback = st.text_area("Feedback (encrypted)", height=140)
        col_a, col_b = st.columns(2)
        with col_a:
            mark = st.form_submit_button("✅ Record mark", type="primary")
        with col_b:
            revise = st.form_submit_button("↩️ Return for revision")

    if mark:
        system.review(chosen, grade, float(score), feedback, password)
        st.success("Mark recorded and feedback sealed.")
        st.rerun()
    if revise:
        system.return_for_revision(chosen, feedback, password)
        st.success("Returned to the student.")
        st.rerun()
