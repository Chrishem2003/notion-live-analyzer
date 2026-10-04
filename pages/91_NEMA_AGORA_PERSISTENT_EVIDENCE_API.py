import tempfile
from pathlib import Path
import streamlit as st
from nema_agora.spatial_evidence_api_hardening import query_persistent_evidence
st.set_page_config(page_title="NEMA-AGORA Persistent Evidence API",layout="wide")
st.title("NEMA-AGORA — Persistent Evidence Query API")
st.info("Phase 83 • SQLite-backed • deterministic • read-only")
with tempfile.TemporaryDirectory() as d:
    st.json(query_persistent_evidence(database_path=str(Path(d)/"evidence.db"),request_id="REQ-DEMO-083",query={"aoi_id":"DEMO-AOI"},limit=100))
