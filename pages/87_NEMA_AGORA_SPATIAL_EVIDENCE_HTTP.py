import streamlit as st
from nema_agora.spatial_evidence_http import handle_request
st.set_page_config(page_title="NEMA-AGORA Spatial Evidence HTTP",layout="wide")
st.title("NEMA-AGORA — Spatial Evidence HTTP Boundary")
st.info("FastAPI-compatible contract • read-only • synthetic demonstration")
st.json(handle_request(request_id="REQ-DEMO-001",operation="QUERY",query={"aoi_id":"DEMO-AOI"},result={"state":"QUERY_READY","count":1,"records":[{"record_id":"EVID-001","aoi_id":"DEMO-AOI"}]}))
