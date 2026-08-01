

import sqlite3
import pandas as pd
import streamlit as st

def render_database_audit_logs():
    """
    Renders an interactive data grid to inspect persistent SQLite logs and sessions.
    """
    st.subheader("? Persistent Database Inspection")
    st.caption("Live audit trail and session records stored in chrishem_engine.db")

    try:
        conn = sqlite3.connect("chrishem_engine.db")
        
        # Fetch system logs
        df_logs = pd.read_sql_query("SELECT * FROM system_logs ORDER BY id DESC LIMIT 100", conn)
        # Fetch user sessions
        df_sessions = pd.read_sql_query("SELECT * FROM user_sessions", conn)
        
        conn.close()

        tab_log, tab_sess = st.tabs([" System Audit Logs", " Active User Sessions"])
        
        with tab_log:
            if not df_logs.empty:
                st.dataframe(df_logs, use_container_width=True, hide_index=True)
            else:
                st.info("No audit logs recorded yet.")

        with tab_sess:
            if not df_sessions.empty:
                st.dataframe(df_sessions, use_container_width=True, hide_index=True)
            else:
                st.info("No active sessions registered.")
                
    except Exception as e:
        st.warning(f"Database inspection notice: {str(e)}")
