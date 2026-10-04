import streamlit as st
from nema_agora.spatial_evidence_service import service_request,adapt_query_result
st.set_page_config(page_title="NEMA-AGORA Spatial Evidence Service",layout="wide")
st.title("NEMA-AGORA — Spatial Evidence Service Boundary")
st.info("Read-only service adapter • synthetic demonstration • no live provider")
q=service_request(request_id="REQ-DEMO-001",operation="QUERY",query={"aoi_id":"DEMO-AOI"})
r=adapt_query_result(q,{"state":"QUERY_READY","count":1,"records":[{"record_id":"EVID-001","aoi_id":"DEMO-AOI"}]})
st.json({"request":q,"response":r})
