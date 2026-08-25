
import sqlite3
import json
import pandas as pd
import streamlit as st
from modules.schema_engine import DB_FILE, init_db, log_provenance

def render_who_surveillance_tab():
    st.subheader("🌐 WHO Global Pathogen Genomic Surveillance Mesh")
    st.caption("Decentralized epidemiological monitoring linking local genomic sequencing directly to international health alert standards.")

    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS who_surveillance_logs (
            alert_id TEXT PRIMARY KEY,
            pathogen_name TEXT,
            variant_clade TEXT,
            geo_location TEXT,
            risk_level TEXT,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🧬 Register Local Genomic Outbreak Sample")
        with st.form("who_form"):
            a_id = st.text_input("Alert ID", value="WHO-SURV-2026-001")
            pathogen = st.selectbox("Pathogen Target", ["SARS-CoV-2", "Influenza A (H5N1)", "Ebolavirus", "Drug-Resistant Tuberculosis"])
            clade = st.text_input("Variant / Clade Designation", value="Omicron-XDV Sublineage")
            location = st.text_input("Sampling Node / Region", value="Arua Regional Health Sector, Uganda")
            risk = st.selectbox("Assessed Risk Tier", ["Low Monitoring", "Moderate Concern", "High Priority Alert"])
            
            sub_who = st.form_submit_button("Broadcast to WHO Mesh Node")
            if sub_who:
                cursor.execute('''
                    INSERT OR REPLACE INTO who_surveillance_logs (alert_id, pathogen_name, variant_clade, geo_location, risk_level)
                    VALUES (?, ?, ?, ?, ?)
                ''', (a_id, pathogen, clade, location, risk))
                conn.commit()
                log_provenance(a_id, "BROADCAST_WHO_SURVEILLANCE", "chief.investigator@lab.org", {"pathogen": pathogen, "risk": risk})
                st.success("Pathogen alert encrypted and broadcast to regional epidemiological node!")
                st.rerun()

    with col2:
        st.markdown("###  Active WHO Surveillance Telemetry")
        surv_df = pd.read_sql_query("SELECT * FROM who_surveillance_logs ORDER BY logged_at DESC", conn)
        if not surv_df.empty:
            st.dataframe(surv_df, use_container_width=True)
        else:
            st.info("No active surveillance alerts logged.")

    conn.close()
