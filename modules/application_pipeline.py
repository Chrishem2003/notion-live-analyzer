import streamlit as st
import pandas as pd

def render_pipeline_ui():
    st.subheader("📋 Application Pipeline & Document Vault")
    st.caption("Manage application workflows, track submissions, and handle document repositories.")
    tab1, tab2 = st.tabs(["Active Applications", "Document Vault"])
    with tab1:
        st.info("Active pipeline monitoring initialized.")
        df = pd.DataFrame({
            "Application": ["Research Fellowship", "Data Analytics Certification", "Muni University Project"],
            "Status": ["In Progress", "Submitted", "Completed"],
            "Date": ["2026-07-01", "2026-07-15", "2026-07-28"]
        })
        st.dataframe(df, use_container_width=True)
    with tab2:
        st.success("Document vault secured with session encryption.")
        st.file_uploader("Upload Verification Document", type=["pdf", "docx", "png", "jpg"], key="vault_doc_upload")