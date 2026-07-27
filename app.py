import streamlit as st
import os
import pandas as pd
from modules.validators import validate_fasta, validate_doi
from modules.backup_engine import export_notion_database_snapshot
from modules.api_safeguards import set_pubmed_key_mode, safe_api_request

st.set_page_config(page_title="Notion Live Research Analyzer", page_icon="🧬", layout="wide")

st.title("🧬 Notion Live Research Analyzer")
st.markdown("*High-Throughput Computational Research & Data Synchronization Workbench*")

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ System Credentials & Settings")
    notion_token = st.text_input("Notion Integration Token", type="password")
    database_id = st.text_input("Notion Database ID")
    pubmed_api_key = st.text_input("PubMed API Key (Optional)", type="password")
    
    if pubmed_api_key:
        set_pubmed_key_mode(has_api_key=True)
        st.caption("🟢 PubMed Rate Limit: 10 req/sec (Key Active)")
    else:
        set_pubmed_key_mode(has_api_key=False)
        st.caption("🟡 PubMed Rate Limit: 2.5 req/sec (Standard)")

    st.markdown("---")
    st.subheader("💾 Quick Backup Trigger")
    if st.button("🚀 Run Instant DB Backup", type="primary"):
        if not notion_token or not database_id:
            st.error("Please supply both Notion Integration Token and Database ID.")
        else:
            with st.spinner("Exporting database snapshot..."):
                try:
                    res = export_notion_database_snapshot(database_id, notion_token)
                    st.success(f"Backup Complete! Extracted {res['record_count']} records.")
                    st.download_button("📥 Download JSON Snapshot", res["raw_json"], file_name="notion_backup.json", mime="application/json")
                    st.download_button("📥 Download CSV Snapshot", res["raw_csv"], file_name="notion_backup.csv", mime="text/csv")
                except Exception as e:
                    st.error(f"Backup failed: {e}")

# --- MAIN NAVIGATION TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["🧬 Genomics & Validation", "📑 Literature Search", "💾 Workspace Backups", "🛡️ System Telemetry"])

with tab1:
    st.subheader("Genomics Sequence Validator")
    seq_input = st.text_area("Paste DNA/RNA FASTA Sequence", height=150)
    if seq_input:
        is_valid = validate_fasta(seq_input)
        if is_valid:
            st.success("✅ Valid FASTA Sequence Format")
            st.metric("Sequence Length (bp)", len(seq_input.replace("\n", "").strip()))
        else:
            st.error("❌ Invalid characters found in sequence. Only standard IUPAC nucleotide codes allowed.")

with tab2:
    st.subheader("Literature Query & DOI Checker")
    doi_val = st.text_input("Enter Paper DOI (e.g., 10.1038/s41586-020-2649-2)")
    if doi_val:
        if validate_doi(doi_val):
            st.success("Valid DOI Format")
        else:
            st.warning("Invalid DOI format structure.")

with tab3:
    st.subheader("Full Database Backup & Snapshot Manager")
    st.info("Run on-demand backups to safeguard research entries before applying bulk Notion database mutations.")
    if st.button("Export Full Database"):
        if notion_token and database_id:
            with st.spinner("Processing..."):
                res = export_notion_database_snapshot(database_id, notion_token)
                st.write(f"Total Records Synchronized: **{res['record_count']}**")
                st.download_button("Download JSON Snapshot", res["raw_json"], file_name="notion_backup.json")
                st.download_button("Download CSV Snapshot", res["raw_csv"], file_name="notion_backup.csv")
        else:
            st.warning("Provide credentials in the sidebar first.")

with tab4:
    st.subheader("Defensive Safeguards & API Telemetry")
    col1, col2, col3 = st.columns(3)
    col1.metric("Notion Rate Cap", "2.5 req/sec", "Safeguard Active")
    col2.metric("PubMed Rate Cap", "10 req/sec" if pubmed_api_key else "2.5 req/sec", "Backoff Active")
    col3.metric("Retry Strategy", "Exponential", "Jitter Enabled")
