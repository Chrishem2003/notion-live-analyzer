import streamlit as st
from nema_agora.spatial_evidence_api import query_spatial_evidence
st.set_page_config(page_title="NEMA-AGORA Spatial Evidence API",layout="wide")
st.title("NEMA-AGORA — Spatial Evidence Query Surface")
st.info("Read-only governed query contract • synthetic demonstration")
records=[{"record_id":"R2","aoi_id":"DEMO-AOI","scene_id":"S2-COMP","candidate_id":"CHANGE-002","review_status":"QUEUED","observed_at":"2026-10-02"},{"record_id":"R1","aoi_id":"DEMO-AOI","scene_id":"S2-BASE","candidate_id":"CHANGE-001","review_status":"CONFIRMED","observed_at":"2026-10-01"}]
st.json(query_spatial_evidence(records,aoi_id="DEMO-AOI"))
