# --- CHRISHEM AUTHOR PROFILE BLOCK ---
import os
import streamlit as st

st.markdown("# **Notion Live Analyzer**")
st.markdown("### **Creator: CHRISHEM**")
st.markdown("---")
# -------------------------------------

import sqlite3
import os
from datetime import datetime

def prune_old_logs(max_records: int = 1000):
    """
    Maintains database performance by pruning system logs beyond the maximum record threshold.
    """
    db_path = "chrishem_engine.db"
    if not os.path.exists(db_path):
        return {"status": "skipped", "reason": "Database not found"}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Count total logs
        cursor.execute("SELECT COUNT(*) FROM system_logs;")
        total_logs = cursor.fetchone()[0]
        
        if total_logs > max_records:
            cursor.execute(f"""
                DELETE FROM system_logs 
                WHERE id NOT IN (
                    SELECT id FROM system_logs ORDER BY id DESC LIMIT {max_records}
                );
            """)
            conn.commit()
            deleted_count = cursor.rowcount
            conn.close()
            return {"status": "success", "pruned_records": deleted_count}
        
        conn.close()
        return {"status": "optimal", "total_records": total_logs}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    result = prune_old_logs()
    print(f"Log Rotator Execution Result: {result}")
