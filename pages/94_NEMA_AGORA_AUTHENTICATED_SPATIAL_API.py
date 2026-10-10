import tempfile
from pathlib import Path
import streamlit as st
from nema_agora.authenticated_spatial_api import authenticated_query
st.set_page_config(page_title="NEMA-AGORA Authenticated Spatial API",layout="wide")
st.title("NEMA-AGORA — Authenticated Spatial Evidence API")
st.info("Phase 86 • authorization → query → repository • synthetic demo")
with tempfile.TemporaryDirectory() as d:
    st.json(authenticated_query(database_path=str(Path(d)/"e.db"),actor_id="ACTOR-DEMO",role="coordinator",request_id="REQ-DEMO-086"))
