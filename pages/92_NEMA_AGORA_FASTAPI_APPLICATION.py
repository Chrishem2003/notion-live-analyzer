import tempfile
from pathlib import Path
import streamlit as st
from nema_agora.fastapi_spatial_evidence_app import app_contract
st.set_page_config(page_title="NEMA-AGORA FastAPI Application",layout="wide")
st.title("NEMA-AGORA — FastAPI Application Wiring")
st.info("Phase 84 • HTTP application contract • read-only")
st.json(app_contract())
with tempfile.TemporaryDirectory() as d:
    st.code(f"GET /api/v1/spatial-evidence/query?request_id=REQ-84&database_path={Path(d)/'evidence.db'}")
