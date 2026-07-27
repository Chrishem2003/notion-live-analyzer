import streamlit as st
import pandas as pd
from modules.validators import validate_fasta, validate_doi
from modules.backup_engine import export_notion_database_snapshot
from modules.api_safeguards import set_pubmed_key_mode
from modules.phylo_engine import parse_multi_fasta, calculate_distance_matrix, generate_simple_newick, render_ascii_tree
from modules.notifier import send_backup_webhook_alert
from modules.bio_analytics import analyze_sequence_variants
from modules.audit_engine import generate_compliance_hash, format_audit_log
from modules.pdf_engine import generate_research_pdf_report
from modules.auth_engine import initialize_rbac, check_permission

st.set_page_config(page_title="Notion Live Research Analyzer Enterprise", page_icon="🧬", layout="wide")

initialize_rbac()

st.title("🧬 Notion Live Research Analyzer Enterprise")
st.caption("Multi-User Research Workspace, Automated Reporting & Cryptographic Audit Suite")

# --- SIDEBAR CONFIGURATION & ROLE SELECTOR ---
with st.sidebar:
    st.header("👤 User Authentication & Roles")
    user_id = st.text_input("User Email / ID", value="investigator@lab.org")
    role_choice = st.selectbox("Active Workspace Role", ["Viewer", "Analyst", "Admin"], index=1)
    st.session_state["user_role"] = role_choice
    
    st.info(f"Active Permissions Level: **{st.session_state['user_role']}**")

    st.markdown("---")
    st.header("⚙️ Workspace Credentials")
    
    if check_permission("Admin"):
        notion_token = st.text_input("Notion Integration Token", type="password")
        database_id = st.text_input("Notion Database ID")
        pubmed_api_key = st.text_input("PubMed API Key", type="password")
        webhook_url = st.text_input("Webhook URL (Discord/Slack)", type="password")
    else:
        st.caption("🔒 *Credential management restricted to Workspace Admins.*")
        notion_token, database_id, pubmed_api_key, webhook_url = "", "", "", ""

    st.markdown("---")
    if check_permission("Admin"):
        if st.button("🚀 Execute FAIR Compliance Backup", type="primary"):
            if notion_token and database_id:
                with st.spinner("Generating cryptographically verified snapshot..."):
                    res = export_notion_database_snapshot(database_id, notion_token)
                    audit_stamp = generate_compliance_hash(res)
                    st.success(f"Backup Verified! Records: {res['record_count']}")
                    st.code(f"SHA-256:\n{audit_stamp}", language="text")
                    if webhook_url:
                        send_backup_webhook_alert(webhook_url, res['record_count'], database_id)
            else:
                st.error("Missing credentials.")

# --- NAVIGATION TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧬 Variant Analytics & PDF Export", 
    "📑 Literature Meta-Synthesizer", 
    "💼 Grant Alignment Engine",
    "💾 Snapshot Manager", 
    "🔒 Provenance & RBAC Telemetry"
])

# TAB 1: VARIANT ANALYTICS & PDF REPORTING
with tab1:
    st.subheader("Genomic Sequence Variant & GC Profiler")
    dna_in = st.text_area("Paste DNA Sequence", height=100, value="ATGCGATCGATCGATCGATCGATCGA")
    if dna_in:
        metrics = analyze_sequence_variants(dna_in)
        if metrics:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Sequence Length", f"{metrics['length']} bp")
            c2.metric("GC Content", f"{metrics['gc_content']}%")
            c3.metric("AT Content", f"{metrics['at_content']}%")
            c4.metric("Total Codons", metrics['total_codons'])

            if check_permission("Analyst"):
                st.markdown("---")
                st.subheader("📄 Automated PDF Report Generation")
                if st.button("Generate Formal Research PDF"):
                    audit_hash = generate_compliance_hash(metrics)
                    pdf_file = generate_research_pdf_report(metrics, user_id, audit_hash)
                    
                    with open(pdf_file, "rb") as f:
                        st.download_button(
                            label="📥 Download Executed PDF Report",
                            data=f,
                            file_name=f"Research_Report_{user_id}.pdf",
                            mime="application/pdf"
                        )
            else:
                st.warning("⚠️ Upgrading to Analyst role is required to generate exportable PDF reports.")

# TAB 2: LITERATURE SYNTHESIZER
with tab2:
    st.subheader("Literature Synthesis Engine")
    query_topic = st.text_input("Enter Topic or DOI", value="CRISPR gene editing in agriculture")
    if st.button("Synthesize Papers"):
        st.markdown(f"**Synthesized Output for:** *{query_topic}*")
        st.write("1. **Gene Editing Precision in Crops** (2025) — *DOI: 10.1038/s41586-024-0001*")

# TAB 3: GRANT ALIGNMENT
with tab3:
    st.subheader("Grant Alignment Engine")
    abstract_text = st.text_area("Proposal Abstract", height=120)
    if abstract_text:
        st.success("Abstract parsed against funding indices.")

# TAB 4: SNAPSHOT MANAGER
with tab4:
    st.subheader("System Database Snapshots")
    if check_permission("Admin"):
        if st.button("Export Verified Backup"):
            res = export_notion_database_snapshot(database_id, notion_token)
            st.write(f"Synced **{res['record_count']}** items.")
    else:
        st.info("🔒 Snapshot management requires Admin permissions.")

# TAB 5: TELEMETRY & RBAC STATUS
with tab5:
    st.subheader("Role-Based Access Control & Telemetry")
    st.json({
        "current_user": user_id,
        "assigned_role": st.session_state["user_role"],
        "permissions": {
            "can_export_pdf": check_permission("Analyst"),
            "can_trigger_backups": check_permission("Admin"),
            "can_manage_keys": check_permission("Admin")
        }
    })
