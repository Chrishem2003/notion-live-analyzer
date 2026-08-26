"""
modules/verification.py
Student free-tier application: uploads go into a REVIEW QUEUE.

Deliberately does NOT auto-approve government ID scans. See the chat
response for why. If you later want to reduce the manual-review load,
plug a real KYC vendor into `run_provider_check()` below (Persona,
Stripe Identity, Smile Identity, Jumio) â€” even then, keep a human
"approve" click before `subscription.grant_student_free()` is called,
so no single automated match can silently grant access.
"""

import sqlite3
import datetime
import os
import streamlit as st

from modules import subscription

DB_PATH = "sovereign_apex_engine.db"
UPLOAD_DIR = "secure_uploads/id_verification"  # move to encrypted object storage in production


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS verification_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            full_name TEXT,
            date_of_birth TEXT,
            institution TEXT,
            id_doc_path TEXT,
            institution_doc_path TEXT,
            status TEXT DEFAULT 'pending',   -- pending | approved | rejected
            provider_check_result TEXT,
            submitted_at TEXT,
            reviewed_at TEXT,
            reviewed_by TEXT
        )
    """)
    conn.commit()
    return conn


def _save_upload(uploaded_file, email, tag):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_email = email.replace("@", "_at_").replace(".", "_")
    fname = f"{safe_email}_{tag}_{int(datetime.datetime.now(datetime.UTC).timestamp())}_{uploaded_file.name}"
    path = os.path.join(UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def run_provider_check(id_doc_path: str) -> dict:
    """
    Stub for a real KYC provider. Wire this up when you have API keys.
    Returns a machine opinion ONLY â€” never auto-grants access on its own.
    """
    return {"provider": "none_configured", "note": "Manual review required â€” no provider connected."}


def submit_application(email, full_name, date_of_birth, institution, id_file, institution_file):
    id_path = _save_upload(id_file, email, "govid") if id_file else None
    inst_path = _save_upload(institution_file, email, "institution") if institution_file else None
    provider_result = run_provider_check(id_path) if id_path else {}

    conn = get_conn()
    conn.execute(
        """INSERT INTO verification_requests
           (email, full_name, date_of_birth, institution, id_doc_path, institution_doc_path,
            status, provider_check_result, submitted_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (email, full_name, str(date_of_birth), institution, id_path, inst_path,
         "pending", str(provider_result), datetime.datetime.now(datetime.UTC).isoformat()),
    )
    conn.commit()
    conn.close()


def render_student_application_form():
    """Drop this into a page (e.g. Home Dashboard, 'Account' tab)."""
    st.markdown("#### ðŸŽ“ Apply for Free Student Access")
    st.caption(
        "Free access for verified students under 26. Upload a photo/scan of your "
        "institution ID and a government-issued ID. A human reviewer approves "
        "applications â€” this is not instant."
    )
    identity = st.session_state.get("user_identity", {})
    email = identity.get("email", "")

    with st.form("student_verification_form"):
        full_name = st.text_input("Full legal name")
        dob = st.date_input("Date of birth")
        institution = st.text_input("University / institution")
        id_file = st.file_uploader("Government-issued ID (photo/scan)", type=["png", "jpg", "jpeg", "pdf"])
        inst_file = st.file_uploader("Institution/student ID (photo/scan)", type=["png", "jpg", "jpeg", "pdf"])
        consent = st.checkbox("I consent to this document being stored for identity review purposes.")
        submitted = st.form_submit_button("Submit for Review")

        if submitted:
            if not (full_name and institution and id_file and inst_file and consent):
                st.error("All fields, both documents, and consent are required.")
            else:
                age = (datetime.date.today() - dob).days // 365
                if age >= 26:
                    st.error("Free student access is limited to applicants under 26.")
                else:
                    submit_application(email, full_name, dob, institution, id_file, inst_file)
                    st.success("âœ… Submitted. You'll be notified once an admin reviews your documents (usually within 2 business days).")


def render_admin_review_queue():
    """Drop this into the Admin & Security Center as a new tab."""
    st.markdown("#### ðŸŽ“ Student Verification â€” Review Queue")
    conn = get_conn()
    pending = conn.execute(
        "SELECT id, email, full_name, institution, submitted_at, id_doc_path, institution_doc_path "
        "FROM verification_requests WHERE status='pending' ORDER BY submitted_at ASC"
    ).fetchall()

    if not pending:
        st.info("No pending applications.")
        conn.close()
        return

    for req_id, email, full_name, institution, submitted_at, id_path, inst_path in pending:
        with st.expander(f"{full_name} â€” {institution} ({email})"):
            st.caption(f"Submitted {submitted_at}")
            c1, c2 = st.columns(2)
            with c1:
                if id_path and os.path.exists(id_path):
                    st.image(id_path, caption="Government ID", width='stretch')
            with c2:
                if inst_path and os.path.exists(inst_path):
                    st.image(inst_path, caption="Institution ID", width='stretch')

            colA, colB = st.columns(2)
            reviewer = st.session_state.get("user_identity", {}).get("name", "Admin")
            if colA.button("âœ… Approve", key=f"approve_{req_id}"):
                conn.execute(
                    "UPDATE verification_requests SET status='approved', reviewed_at=?, reviewed_by=? WHERE id=?",
                    (datetime.datetime.now(datetime.UTC).isoformat(), reviewer, req_id),
                )
                conn.commit()
                subscription.grant_student_free(email)
                st.success(f"Approved. {email} now has free student access.")
                st.rerun()
            if colB.button("âŒ Reject", key=f"reject_{req_id}"):
                conn.execute(
                    "UPDATE verification_requests SET status='rejected', reviewed_at=?, reviewed_by=? WHERE id=?",
                    (datetime.datetime.now(datetime.UTC).isoformat(), reviewer, req_id),
                )
                conn.commit()
                st.warning("Rejected.")
                st.rerun()
    conn.close()


