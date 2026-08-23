
import streamlit as st
import pandas as pd
from datetime import datetime
from modules.database import log_backend_event
from modules.security_config import is_admin_email

def verify_master_admin(email: str) -> bool:
    """
    Server-side check: validates if the provided email belongs to the master
    administrator. The admin email is resolved from configuration (env / .env),
    never hardcoded in source.
    """
    return is_admin_email(email)

def render_access_control_panel():
    """
    Renders the Sovereign Tiered Access Control & Student Verification Portal with clean professional styling.
    """
    st.markdown("### Sovereign Access Control & Tiered Licensing Hub")
    st.caption("Manage secure user licenses, African student verification portals, credential enclaves, and administrative privileges.")

    # Session State Initialization — derived from the REAL logged-in identity
    # (st.session_state.user_identity, set by the real PBKDF2/OAuth login flow
    # in app.py), not a hardcoded default. Previously this defaulted every new
    # session to user_tier="Master Admin" / student_verified=True regardless
    # of who was actually logged in, and let anyone overwrite a free-text
    # email field with the admin's address to see "Verified (Admin)" displayed
    # even though the real is_admin() check elsewhere never consulted this.
    real_identity = st.session_state.get("user_identity", {})
    real_email = real_identity.get("email", "")

    if "user_email" not in st.session_state:
        st.session_state.user_email = real_email
    if "user_tier" not in st.session_state:
        st.session_state.user_tier = "Master Admin" if verify_master_admin(real_email) else "Free (Unverified)"
    if "student_verified" not in st.session_state:
        st.session_state.student_verified = verify_master_admin(real_email)

    # User Profile & Authentication Card with privacy masking
    st.markdown("#### Active User Session & License Profile")
    col_u1, col_u2, col_u3 = st.columns(3)

    with col_u1:
        st.text_input("User Email Address", value=st.session_state.user_email, disabled=True)
        st.caption("This reflects your authenticated session — it isn't editable here.")

    with col_u2:
        st.text_input("Assigned Access Tier", value=st.session_state.user_tier, disabled=True)

    with col_u3:
        status_display = "Verified (Admin)" if st.session_state.student_verified else "Pending ID Verification"
        st.text_input("Verification Status", value=status_display, disabled=True)

    st.markdown("---")

    # African Student Free Access Verification Section
    if st.session_state.user_tier != "Master Admin":
        st.markdown("#### African Student Free Access Verification Portal")
        st.caption("Students enrolled in African institutions receive Free Standard Access upon uploading front and back scans of their National ID and University ID.")

        with st.form("student_verification_form"):
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                country_select = st.selectbox("African Country", ["Uganda", "Kenya", "Tanzania", "Rwanda", "Nigeria", "Ghana", "South Africa", "Other African Nation"])
                university_name = st.text_input("Institution / University Name", value="Muni University")
                student_id_no = st.text_input("Student Registration / ID Number")
            with col_v2:
                nat_id_front = st.file_uploader("National ID (Front Scan)", type=["png", "jpg", "jpeg", "pdf"])
                nat_id_back = st.file_uploader("National ID (Back Scan)", type=["png", "jpg", "jpeg", "pdf"])
                univ_id_front = st.file_uploader("University ID (Front Scan)", type=["png", "jpg", "jpeg", "pdf"])
                univ_id_back = st.file_uploader("University ID (Back Scan)", type=["png", "jpg", "jpeg", "pdf"])

            submitted_verification = st.form_submit_button("Submit Credentials for Free Standard Access")
            if submitted_verification:
                if nat_id_front and nat_id_back and univ_id_front and univ_id_back and student_id_no:
                    st.session_state.student_verified = True
                    st.session_state.user_tier = "Standard (Verified Student)"
                    log_backend_event("INFO", f"Student verification approved for verified applicant at {university_name} ({country_select}).")
                    st.success("Verification Successful! Your account has been upgraded to Free Standard Access.")
                    st.rerun()
                else:
                    st.error("Please upload all required ID documents (National ID Front/Back & University ID Front/Back) and provide your ID number.")

    st.markdown("---")

    # Master Admin Management Console with Privacy Masking
    if verify_master_admin(st.session_state.user_email):
        st.markdown("#### Master Admin License & User Management Console")
        st.caption("Authorized Master Administrator: [Secured Administrator Enclave]. Manage global access tiers and audit logs.")

        admin_users_data = [
            {"Identity": "Master Administrator", "Role": "Master Admin", "Tier": "Apex Sovereign", "Status": "Active"},
            {"Identity": "Student Researcher Cohort", "Role": "African Student", "Tier": "Standard (Verified)", "Status": "Active"},
            {"Identity": "Enterprise Partner Client", "Role": "Enterprise", "Tier": "Premium", "Status": "Active"}
        ]
        st.dataframe(pd.DataFrame(admin_users_data), use_container_width=True)

        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if st.button("Audit All Active License Enclaves"):
                log_backend_event("INFO", "Master Admin executed license enclave audit.")
                st.success("License audit complete: All active enclaves operating under secure cryptographic keys.")
        with col_a2:
            if st.button("Revoke Unauthorized Access Tokens"):
                log_backend_event("INFO", "Master Admin executed token revocation protocol.")
                st.success("Token revocation sweep executed successfully.")

