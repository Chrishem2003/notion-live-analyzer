import streamlit as st
import streamlit.components.v1 as components
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
from modules.ncbi_engine import fetch_ncbi_gene_summary
from modules.satellite_engine import fetch_field_site_telemetry
from modules.knowledge_graph import build_research_knowledge_graph
from modules.proteomics_engine import translate_dna_to_protein, fetch_pdb_metadata
from modules.structure_viewer import render_structure_viewer_tab
from modules.grant_engine import render_grant_engine_tab
from modules.inventory_engine import render_inventory_tab
from modules.schema_engine import render_schema_engine_tab
from modules.grant_matcher import render_grant_matcher_tab

st.set_page_config(page_title="World-Record Autonomous Research Platform", page_icon="🧬", layout="wide")

initialize_rbac()

st.title("🌐 World-Record Autonomous Research Intelligence System (ResearchOS)")
st.caption("Genomics • 3D Proteomics • Satellite Telemetry • Grant Indexer • FAIR Database Schema • Inventory & Lab Workflows")

# --- SIDEBAR AUTHENTICATION & SETTINGS ---
with st.sidebar:
    st.header("👤 User Authentication")
    user_id = st.text_input("User ID / Email", value="chief.investigator@lab.org")
    role_choice = st.selectbox("Workspace Role", ["Viewer", "Analyst", "Admin"], index=2)
    st.session_state["user_role"] = role_choice
    
    st.markdown("---")
    st.header("⚙️ Workspace Credentials")
    if check_permission("Admin"):
        notion_token = st.text_input("Notion Token", type="password")
        database_id = st.text_input("Notion Database ID")
        pubmed_api_key = st.text_input("NCBI/PubMed API Key", type="password")
        webhook_url = st.text_input("Webhook URL", type="password")
    else:
        st.caption("🔒 Admin role required to view credentials.")
        notion_token, database_id, pubmed_api_key, webhook_url = "", "", "", ""

    if check_permission("Admin"):
        st.markdown("---")
        if st.button("🚀 Run FAIR Verified Backup", type="primary"):
            if notion_token and database_id:
                res = export_notion_database_snapshot(database_id, notion_token)
                stamp = generate_compliance_hash(res)
                st.success(f"Backup Verified! Records: {res['record_count']}")
                st.code(stamp, language="text")
                if webhook_url:
                    send_backup_webhook_alert(webhook_url, res['record_count'], database_id)

# --- MASTER NAVIGATION TABS ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
    "🧬 Genomics & NCBI", 
    "🧪 Transl. Proteomics",
    "🖥️ 3D Structure Viewer",
    "🧫 Lab Inventory & PCR",
    "🛰️ Satellite Intelligence", 
    "🕸️ Knowledge Graph",
    "🎯 Grant Indexer & Matcher",
    "📄 AI Grant Drafter",
    "🗄️ Unified DB Schema",
    "📊 PDF Report Generator",
    "🔒 Provenance & Audit"
])

# TAB 1: GENOMICS & NCBI
with tab1:
    st.subheader("NCBI Direct Fetch & Genomic Variant Profiler")
    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        st.markdown("### 🔍 NCBI Gene Locus Fetcher")
        gene_query = st.text_input("Gene Symbol / Term", value="BRCA1")
        if st.button("Fetch NCBI Summary"):
            with st.spinner("Querying NCBI Entrez API..."):
                ncbi_res = fetch_ncbi_gene_summary(gene_query, pubmed_api_key)
                st.json(ncbi_res)

    with col_b:
        st.markdown("### 🧬 Sequence Variant Analytics")
        dna_in = st.text_area("Paste DNA Sequence", height=100, value="ATGCGATCGATCGATCGATCGATCGA")
        if dna_in:
            metrics = analyze_sequence_variants(dna_in)
            if metrics:
                st.metric("GC Content", f"{metrics['gc_content']}%")
                st.metric("Length", f"{metrics['length']} bp")

# TAB 2: TRANSLATIONAL PROTEOMICS
with tab2:
    st.subheader("Translational Proteomics & Structure Data Engine")
    p_col1, p_col2 = st.columns(2)
    
    with p_col1:
        st.markdown("### 🧬 DNA -> Amino Acid Translation")
        dna_prot_in = st.text_area("Paste Coding DNA", height=100, value="ATGGCCATTGTAATGGGCCGCTGAAAG")
        if st.button("Translate to Protein"):
            translation = translate_dna_to_protein(dna_prot_in)
            st.code(translation["protein_sequence"], language="text")
            m1, m2 = st.columns(2)
            m1.metric("Amino Acids", translation["aa_count"])
            m2.metric("Est. Mol Weight", f"{translation['est_mol_weight_kDa']} kDa")

    with p_col2:
        st.markdown("### 🏛️ RCSB PDB Metadata Lookup")
        pdb_id_input = st.text_input("Enter PDB Code", value="1TUP")
        if st.button("Fetch PDB Metadata"):
            pdb_info = fetch_pdb_metadata(pdb_id_input)
            st.json(pdb_info)

# TAB 3: 3D STRUCTURE VIEWER
with tab3:
    render_structure_viewer_tab()

# TAB 4: LAB INVENTORY & PCR CALCULATOR
with tab4:
    render_inventory_tab()

# TAB 5: SATELLITE TELEMETRY
with tab5:
    st.subheader("Satellite Environmental Monitoring for Field Research Sites")
    col_lat, col_lon = st.columns(2)
    lat_val = col_lat.number_input("Latitude", value=3.0300)
    lon_val = col_lon.number_input("Longitude", value=30.9100)
    
    if st.button("Query Satellite Telemetry"):
        with st.spinner("Pulling satellite indices..."):
            telemetry = fetch_field_site_telemetry(lat_val, lon_val)
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("NDVI Index", telemetry["ndvi_index"])
            t2.metric("Vegetation Health", telemetry["vegetation_health"])
            t3.metric("Surface Temp", f"{telemetry['surface_temp_c']} °C")
            t4.metric("Soil Moisture", telemetry["moisture_index"])

# TAB 6: KNOWLEDGE GRAPH
with tab6:
    st.subheader("Interactive Research Knowledge Graph")
    if st.button("Render Knowledge Graph Network"):
        graph_file = build_research_knowledge_graph([])
        with open(graph_file, "r", encoding="utf-8") as f:
            components.html(f.read(), height=480)

# TAB 7: AUTOMATED GRANT INDEXER
with tab7:
    render_grant_matcher_tab()

# TAB 8: AI GRANT DRAFTER
with tab8:
    render_grant_engine_tab()

# TAB 9: UNIFIED DATABASE SCHEMA
with tab9:
    render_schema_engine_tab()

# TAB 10: PDF REPORT EXPORT
with tab10:
    st.subheader("Publication-Ready PDF Generator")
    if check_permission("Analyst"):
        if st.button("Generate Enterprise PDF Report"):
            dummy_metrics = {"length": 150, "gc_content": 52.4, "at_content": 47.6, "total_codons": 50}
            stamp = generate_compliance_hash(dummy_metrics)
            pdf_path = generate_research_pdf_report(dummy_metrics, user_id, stamp)
            
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download PDF Report", data=f, file_name="Research_Report.pdf", mime="application/pdf")
    else:
        st.warning("Analyst permission required.")

# TAB 11: PROVENANCE & AUDIT
with tab11:
    st.subheader("System Telemetry & FAIR Compliance Audit")
    st.json({
        "platform_status": "ONLINE",
        "active_user": user_id,
        "assigned_role": st.session_state["user_role"],
        "active_modules": [
            "NCBI Entrez API",
            "3Dmol.js WebGL Engine",
            "Lab Inventory & Reaction Calculator",
            "Automated Grant Matcher",
            "AI Grant Generator",
            "SQLite Unified Research Schema",
            "Sentinel-2 Environmental Telemetry",
            "Vis.js Knowledge Graph",
            "SHA-256 FAIR Provenance Ledger"
        ]
    })
