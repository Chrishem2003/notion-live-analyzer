import tempfile
from pathlib import Path
import streamlit as st
from nema_agora.spatial_evidence_sqlite_repository import SQLiteSpatialEvidenceRepository
st.set_page_config(page_title="NEMA-AGORA SQLite Repository",layout="wide")
st.title("NEMA-AGORA — SQLite Spatial Evidence Repository")
st.info("Phase 81 prototype • append-only persistence • synthetic evidence")
with tempfile.TemporaryDirectory() as d:
    repo=SQLiteSpatialEvidenceRepository(str(Path(d)/"demo.db"))
    st.write("Repository ready:",repo.database_path)
    st.write("Records:",repo.list())
