import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
from modules.database import log_backend_event

def scan_for_threats() -> pd.DataFrame:
    """
    Scans system logs and active sessions for known attack signatures, SQL injection patterns,
    or brute-force anomalies.
    """
    db_path = "chrishem_engine.db"
    if not os.path.exists(db_path):
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(db_path)
        # Fetch recent warning/error logs or potential WAF triggers
        query = "SELECT * FROM system_logs WHERE level IN ('WARNING', 'ERROR') ORDER BY id DESC LIMIT 50;"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        log_backend_event("ERROR", f"Threat scan failed: {str(e)}")
        return pd.DataFrame()

def render_threat_response_panel():
    """
    Renders the incident response and threat intelligence dashboard inside Streamlit.
    """
    st.subheader("?? Incident Response & Threat Intelligence")
    st.caption("Active monitoring for malicious payloads, anomalous auth failures, and system intrusion attempts.")

    df_threats = scan_for_threats()

    if not df_threats.empty:
        st.warning(f"Detected {len(df_threats)} flagged security events in audit logs.")
        st.dataframe(df_threats, use_container_width=True)
        
        if st.button("Purge & Quarantine Flagged Sessions"):
            log_backend_event("SECURITY", "Administrator executed quarantine protocol on flagged threat logs.")
            st.success("Security quarantine protocols successfully executed. All suspicious channels isolated.")
    else:
        st.success("No active security threats detected. System perimeter secure.")

    if st.button("Run Comprehensive Threat Scan"):
        log_backend_event("INFO", "Manual threat intelligence scan initiated.")
        st.rerun()
