import streamlit as st
import pandas as pd
from datetime import datetime
from modules.database import log_backend_event

def init_pipeline_session_state():
    """
    Initializes session state variables for the application pipeline module.
    """
    if "pipeline_submissions" not in st.session_state:
        st.session_state.pipeline_submissions = pd.DataFrame(columns=["Timestamp", "Applicant", "Category", "Status"])

def render_application_pipeline_panel():
    """
    Renders the application pipeline management panel.
    """
    init_pipeline_session_state()
    st.subheader("📋 Application & Research Pipeline Manager")
    st.caption("Manage, track, and filter institutional submissions, academic research applications, and candidate portfolios.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Submissions", len(st.session_state.pipeline_submissions), delta="Active")
    with col2:
        st.metric("Review Status", "Optimized", delta="Secure")
    with col3:
        st.metric("Sync Engine", "Local SQLite", delta="Real-Time")

    st.markdown("---")
    st.markdown("### 📥 Submission Ledger")
    if len(st.session_state.pipeline_submissions) > 0:
        st.dataframe(st.session_state.pipeline_submissions, use_container_width=True)
    else:
        st.info("No active pipeline submissions logged yet. Use the intake forms to log new entries.")

    with st.form("quick_pipeline_form"):
        applicant_name = st.text_input("Applicant / Project Name", value="Kula Chris")
        category = st.selectbox("Submission Category", ["Academic Research", "Professional CV", "Portfolio Review", "Grant Application"])
        submitted = st.form_submit_button("✨ Log New Pipeline Entry")
        if submitted:
            new_row = pd.DataFrame([{"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Applicant": applicant_name, "Category": category, "Status": "Pending Review"}])
            st.session_state.pipeline_submissions = pd.concat([st.session_state.pipeline_submissions, new_row], ignore_index=True)
            log_backend_event("INFO", f"Logged new pipeline entry for {applicant_name} under {category}.")
            st.success("Pipeline entry successfully logged!")
            st.rerun()
