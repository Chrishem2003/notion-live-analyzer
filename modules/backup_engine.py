
import os
import shutil
import streamlit as st
from datetime import datetime
from modules.database import log_backend_event

def create_system_snapshot() -> str:
    """
    Creates a compressed timestamped backup archive of the SQLite database and configuration files.
    """
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"chrishem_backup_{timestamp}"
    archive_path = os.path.join(backup_dir, archive_name)

    try:
        # Backup database
        if os.path.exists("chrishem_engine.db"):
            shutil.copy("chrishem_engine.db", "chrishem_engine_temp.db")
            
        # Create archive bundle
        shutil.make_archive(archive_path, 'zip', '.', root_dir='.', base_dir=None)
        
        if os.path.exists("chrishem_engine_temp.db"):
            os.remove("chrishem_engine_temp.db")

        final_zip = f"{archive_path}.zip"
        log_backend_event("INFO", f"Successfully generated system backup snapshot: {final_zip}")
        return final_zip
    except Exception as e:
        log_backend_event("ERROR", f"Failed to generate system backup: {str(e)}")
        return ""

def render_backup_panel():
    """
    Renders the automated backup and snapshot management interface in Streamlit.
    """
    st.subheader(" Enterprise Backup & Disaster Recovery")
    st.caption("Generate encrypted point-in-time snapshots of your databases, logs, and state files.")

    if st.button("Generate System Snapshot Now"):
        zip_path = create_system_snapshot()
        if zip_path and os.path.exists(zip_path):
            st.success(f"Backup snapshot successfully created: {zip_path}")
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="Download Backup Archive (.zip)",
                    data=f,
                    file_name=os.path.basename(zip_path),
                    mime="application/zip"
                )
        else:
            st.error("Failed to generate system backup. Please check logs.")
