
import sqlite3
import json
import pandas as pd
import streamlit as st
from modules.schema_engine import DB_FILE, init_db, log_provenance

def render_mastercard_impact_tab():
    st.subheader("ðŸ’³ MasterCard Foundation Youth & Agri-Tech Economic Hub")
    st.caption("Empowering grassroots digital entrepreneurship, local resource tracking, and transparent micro-grant financial auditing.")

    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS youth_enterprise_ventures (
            venture_id TEXT PRIMARY KEY,
            founder_name TEXT,
            sector TEXT,
            funding_allocated_usd REAL,
            impact_metrics TEXT,
            status TEXT DEFAULT 'Active'
        );
    ''')
    conn.commit()

    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.markdown("### ðŸš€ Register Local Youth Enterprise & Agri-Tech Venture")
        with st.form("mcf_form"):
            v_id = st.text_input("Venture ID", value="MCF-ENT-2026-01")
            founder = st.text_input("Lead Entrepreneur / Researcher", value="Kula Chris")
            sector = st.selectbox("Venture Sector", ["Agri-Tech & Food Security", "Digital Health Infrastructure", "Green Energy & Waste Management", "Bioinformatics & EdTech"])
            funding = st.number_input("Micro-Grant Allocation (USD)", value=25000.00)
            metrics = st.text_area("Expected Community Impact Target", value="Deploy localized soil sensor telemetry and train 150 local smallholder farmers in digital crop monitoring.")
            
            sub_mcf = st.form_submit_button("Submit Venture for Institutional Audit")
            if sub_mcf:
                cursor.execute('''
                    INSERT OR REPLACE INTO youth_enterprise_ventures (venture_id, founder_name, sector, funding_allocated_usd, impact_metrics)
                    VALUES (?, ?, ?, ?, ?)
                ''', (v_id, founder, sector, funding, metrics))
                conn.commit()
                log_provenance(v_id, "REGISTER_MCF_VENTURE", "chief.investigator@lab.org", {"sector": sector, "funding": funding})
                st.success("Venture securely logged to institutional impact tracker!")
                st.rerun()

    with col_m2:
        st.markdown("### ðŸ“ˆ Active Sponsored Portfolios")
        mcf_df = pd.read_sql_query("SELECT * FROM youth_enterprise_ventures", conn)
        if not mcf_df.empty:
            st.dataframe(mcf_df, use_container_width=True)
        else:
            st.info("No ventures registered yet.")

    conn.close()
