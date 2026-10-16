"""Persistent encrypted research-submission portal.

Configuration:
- AUDIT_PORTAL_ENCRYPTION_PASSWORD: strong server-side encryption passphrase.
- AUDIT_PORTAL_PROFESSOR_PASSWORD: separate password for professor access.

Configure both in Streamlit secrets or environment variables before using this page.
"""
from __future__ import annotations

import streamlit as st

from modules.audit_portal import CHRISHEMSubmissionSystem
from modules.audit_portal_service import (
    PortalConfigurationError,
    load_portal_credentials,
    verify_professor_password,
)


st.set_page_config(page_title="Research Submission Portal", page_icon="🔐", layout="wide")


def _load_credentials() -> tuple[str, str]:
    try:
        configured_secrets = st.secrets
    except Exception:
        configured_secrets = {}
    return load_portal_credentials(configured_secrets)


st.title("🔐 Research Submission Portal")
st.caption(
    "Persistent encrypted submissions with a gated professor review queue. "
    "This page does not generate AI-authorship or plagiarism scores."
)

try:
    encryption_password, professor_password = _load_credentials()
except PortalConfigurationError:
    st.error(
        "The portal is not configured yet. Add both required secrets to Streamlit "
        "secrets or the application environment before accepting submissions."
    )
    st.code(
        'AUDIT_PORTAL_ENCRYPTION_PASSWORD = "use-a-long-random-secret"\n'
        'AUDIT_PORTAL_PROFESSOR_PASSWORD = "use-a-different-long-random-secret"',
        language="toml",
    )
    st.stop()

portal = CHRISHEMSubmissionSystem()

submit_tab, review_tab = st.tabs(["Submit research", "Professor review"])

with submit_tab:
    st.subheader("Submit research securely")
    st.write(
        "Your submission is encrypted before it is stored. Keep your original copy. "
        "Only submit material you are authorized to share with this research workspace."
    )
    with st.form("live_research_submission_form", clear_on_submit=False):
        project_id = st.number_input("Project ID", min_value=1, value=1, step=1)
        student_name = st.text_input("Researcher / student name")
        student_email = st.text_input("Contact email (optional)")
        title = st.text_input("Submission title")
        content = st.text_area(
            "Research content",
            height=300,
            placeholder="Paste your manuscript, report, analysis, or research notes here.",
        )
        submit_clicked = st.form_submit_button("Encrypt and submit", type="primary")

    if submit_clicked:
        if not student_name.strip() or not title.strip() or not content.strip():
            st.error("Name, title, and research content are required.")
        else:
            try:
                result = portal.submit(
                    project_id=int(project_id),
                    student_name=student_name.strip(),
                    title=title.strip(),
                    content=content,
                    password=encryption_password,
                    student_email=student_email.strip(),
                )
            except Exception:
                st.error(
                    "The submission could not be saved securely. No success has been recorded; "
                    "check the server configuration and application logs."
                )
            else:
                st.success(
                    f"Submission #{result['id']} was encrypted and stored successfully."
                )
                st.code(result["blockchain_hash"], language="text")
                st.caption(
                    "The hash is an integrity reference, not proof of authorship or a public blockchain transaction."
                )

with review_tab:
    st.subheader("Professor review queue")
    st.write("Professor access is checked against a separately configured secret.")
    with st.form("professor_access_form"):
        candidate_password = st.text_input(
            "Professor access password", type="password", autocomplete="current-password"
        )
        unlock_clicked = st.form_submit_button("Unlock review queue")

    if unlock_clicked:
        st.session_state["audit_portal_professor_authenticated"] = verify_professor_password(
            candidate_password, professor_password
        )
        if not st.session_state["audit_portal_professor_authenticated"]:
            st.error("Access denied. The password was not accepted.")

    if st.session_state.get("audit_portal_professor_authenticated", False):
        if st.button("Lock review queue", key="audit_portal_lock_review"):
            st.session_state["audit_portal_professor_authenticated"] = False
            st.rerun()

        try:
            submissions = portal.get_submissions()
        except Exception:
            st.error("The submission queue could not be loaded.")
            submissions = []

        if not submissions:
            st.info("No submissions are currently available for review.")
        else:
            safe_queue = [
                {
                    "Submission ID": row["id"],
                    "Project ID": row["project_id"],
                    "Researcher": row["student_name"],
                    "Title": row["title"],
                    "Status": row["status"],
                    "Submitted": row["submitted_at"],
                }
                for row in submissions
            ]
            st.dataframe(safe_queue, use_container_width=True, hide_index=True)

            row_by_id = {int(row["id"]): row for row in submissions}
            submission_id = st.selectbox(
                "Choose a submission",
                options=list(row_by_id),
                format_func=lambda item: (
                    f"#{item} — {row_by_id[item]['student_name']} — "
                    f"{row_by_id[item]['title']} [{row_by_id[item]['status']}]"
                ),
            )
            selected = portal.get_submission(int(submission_id))
            if selected:
                try:
                    decrypted_content = portal.decrypt_submission(
                        int(submission_id), encryption_password
                    )
                except Exception:
                    decrypted_content = None
                    st.error(
                        "The selected submission could not be decrypted with the configured "
                        "encryption secret. Do not change its status until the key is restored."
                    )

                if decrypted_content is not None:
                    st.markdown("#### Submitted content")
                    st.text_area(
                        "Decrypted submission (read-only)",
                        value=decrypted_content,
                        height=260,
                        disabled=True,
                        key=f"review_content_{submission_id}",
                    )
                    with st.form(f"review_submission_{submission_id}"):
                        grade = st.selectbox("Grade", ["A", "B", "C", "D", "F", "Pass", "Fail"])
                        score = st.number_input(
                            "Score (0–100)", min_value=0.0, max_value=100.0, value=0.0, step=1.0
                        )
                        feedback = st.text_area("Feedback to record", height=150)
                        action = st.radio(
                            "Decision",
                            ["Approve and grade", "Return for revision"],
                            horizontal=True,
                        )
                        save_review = st.form_submit_button("Save review decision", type="primary")

                    if save_review:
                        if not feedback.strip():
                            st.error("Add feedback before saving a review decision.")
                        else:
                            try:
                                if action == "Approve and grade":
                                    portal.review(
                                        int(submission_id),
                                        grade,
                                        float(score),
                                        feedback.strip(),
                                        professor_password=encryption_password,
                                    )
                                else:
                                    portal.return_for_revision(
                                        int(submission_id),
                                        feedback.strip(),
                                        professor_password=encryption_password,
                                    )
                            except Exception:
                                st.error("The review decision could not be saved.")
                            else:
                                st.success("Review decision saved.")
                                st.rerun()

st.divider()
st.caption(
    "Operational note: protect and back up the configured encryption secret. Existing records "
    "cannot be decrypted if the secret used to encrypt them is lost. Use a unique, strong secret "
    "and keep the professor access password different from it."
)
