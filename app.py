import streamlit as st
import pandas as pd
from modules.validators import validate_fasta, validate_doi
from modules.backup_engine import export_notion_database_snapshot
from modules.api_safeguards import set_pubmed_key_mode
from modules.phylo_engine import parse_multi_fasta, calculate_distance_matrix, generate_simple_newick, render_ascii_tree
from modules.notifier import send_backup_webhook_alert

st.set_page_config(page_title="Notion Live Research Analyzer", page_icon="🧬", layout="wide")

st.title("🧬 Notion Live Research Analyzer")
st.markdown("*High-Throughput Computational Research & Data Synchronization Workbench*")

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ System Credentials")
    notion_token = st.text_input("Notion Integration Token", type="password")
    database_id = st.text_input("Notion Database ID")
    pubmed_api_key = st.text_input("PubMed API Key (Optional)", type="password")
    webhook_url = st.text_input("Discord/Slack Webhook URL (Optional)", type="password")
    
    if pubmed_api_key:
        set_pubmed_key_mode(has_api_key=True)
        st.caption("🟢 PubMed Rate Limit: 10 req/sec")
    else:
        set_pubmed_key_mode(has_api_key=False)
        st.caption("🟡 PubMed Rate Limit: 2.5 req/sec")

    st.markdown("---")
    st.subheader("💾 Instant Backup")
    if st.button("🚀 Run Backup", type="primary"):
        if not notion_token or not database_id:
            st.error("Missing Notion Token or DB ID.")
        else:
            with st.spinner("Processing backup..."):
                try:
                    res = export_notion_database_snapshot(database_id, notion_token)
                    st.success(f"Backup Complete! {res['record_count']} records.")
                    
                    if webhook_url:
                        alert_sent = send_backup_webhook_alert(webhook_url, res['record_count'], database_id)
                        if alert_sent:
                            st.caption("🔔 Webhook notification dispatched!")

                    st.download_button("Download JSON", res["raw_json"], file_name="notion_backup.json")
                    st.download_button("Download CSV", res["raw_csv"], file_name="notion_backup.csv")
                except Exception as e:
                    st.error(f"Backup error: {e}")

# --- MAIN TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["🧬 Genomics & Phylogenetics", "📑 Literature", "💾 Backup Engine", "🛡️ Telemetry & Alerts"])

with tab1:
    st.subheader("Multi-Sequence Alignment & Phylogenetics")
    fasta_input = st.text_area(
        "Paste Multi-FASTA Sequences",
        height=200,
        value=">Seq_1\nATCGGCTAAGCT\n>Seq_2\nATCGGCTCAGCT\n>Seq_3\nATCCCCTAAGCT"
    )
    if st.button("Run Alignment & Generate Tree"):
        try:
            records = parse_multi_fasta(fasta_input)
            names, dist_matrix = calculate_distance_matrix(records)
            newick_str = generate_simple_newick(names, dist_matrix)
            ascii_tree = render_ascii_tree(names)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🌲 Visual Tree")
                st.code(ascii_tree, language="text")
                st.markdown("### 📄 Newick Output")
                st.code(newick_str, language="text")

            with col2:
                st.markdown("### 📊 Distance Matrix")
                df_matrix = pd.DataFrame(dist_matrix, index=names, columns=names)
                st.dataframe(df_matrix)

        except Exception as e:
            st.error(f"Alignment error: {e}")

with tab2:
    st.subheader("Literature Checker")
    doi_val = st.text_input("Enter Paper DOI")
    if doi_val:
        if validate_doi(doi_val):
            st.success("Valid DOI Format")
        else:
            st.warning("Invalid DOI structure.")

with tab3:
    st.subheader("Workspace Snapshots")
    if st.button("Export DB Snapshot"):
        if notion_token and database_id:
            res = export_notion_database_snapshot(database_id, notion_token)
            st.write(f"Synced **{res['record_count']}** entries.")
            if webhook_url:
                send_backup_webhook_alert(webhook_url, res['record_count'], database_id)
            st.download_button("Download JSON", res["raw_json"], file_name="backup.json")
            st.download_button("Download CSV", res["raw_csv"], file_name="backup.csv")
        else:
            st.warning("Supply credentials in sidebar.")

with tab4:
    st.subheader("System Telemetry")
    st.json({
        "rate_limiters": {"notion": "2.5 req/sec", "pubmed": "10 req/sec" if pubmed_api_key else "2.5 req/sec"},
        "webhook_status": "Configured" if webhook_url else "Disabled"
    })
