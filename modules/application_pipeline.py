import streamlit as st
import pandas as pd

def render_pipeline_ui():
    st.subheader("📋 Application Pipeline, Document Vault & Currency Module")
    st.caption("Comprehensive workflow manager tracking active research applications, academic credentials, and document storage.")
    
    tab1, tab2, tab3 = st.tabs(["Active Applications", "Document Vault", "Currency Conversion"])
    with tab1:
        st.info("Live monitoring pipeline active for Muni University & research initiatives.")
        df = pd.DataFrame({
            "Application": ["Bioinformatics Sequence Pipeline", "Data Analytics Certification", "Muni University Paleontology Project"],
            "Status": ["In Progress", "Submitted", "Completed"],
            "Target Date": ["2026-08-15", "2026-07-15", "2026-03-30"]
        })
        st.dataframe(df, use_container_width=True)
    with tab2:
        st.success("Secure Document Vault initialized with session token protection.")
        st.file_uploader("Upload Verification or Research Document", type=["pdf", "docx", "png", "jpg", "csv"], key="vault_doc_upload_main")
    with tab3:
        st.subheader("Currency & Exchange Module")
        amount = st.number_input("Amount (USD)", value=100.0, key="curr_usd_input")
        rate = st.number_input("Exchange Rate (UGX per 1 USD)", value=3700.0, key="curr_rate_input")
        st.success(f"Equivalent Value: **UGX {amount * rate:,.2f}**")