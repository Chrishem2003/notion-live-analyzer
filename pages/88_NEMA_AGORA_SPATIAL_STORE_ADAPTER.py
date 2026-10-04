import streamlit as st
from nema_agora.spatial_evidence_store_adapter import InMemoryEvidenceRepository,execute_query
st.set_page_config(page_title="NEMA-AGORA Spatial Store Adapter",layout="wide")
st.title("NEMA-AGORA — Spatial Evidence Store Adapter")
st.info("Read-only repository adapter • synthetic demonstration")
repo=InMemoryEvidenceRepository([{"record_id":"EVID-001","aoi_id":"DEMO-AOI","scene_id":"S2-COMP"}])
st.json(execute_query(repository=repo,request_id="REQ-DEMO-001",query={"aoi_id":"DEMO-AOI"}))
