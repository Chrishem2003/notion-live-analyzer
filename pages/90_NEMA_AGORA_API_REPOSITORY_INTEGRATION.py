import streamlit as st
from nema_agora.spatial_evidence_integration import retrieve_spatial_evidence
class DemoRepository:
    def list(self,**filters):
        return [{"record_id":"EVID-001","aoi_id":"DEMO-AOI","scene_id":"S2-DEMO"}] if filters.get("aoi_id") in (None,"DEMO-AOI") else []
st.set_page_config(page_title="NEMA-AGORA API Repository Integration",layout="wide")
st.title("NEMA-AGORA — API → Repository Integration")
st.info("Phase 82 • read-only • governed retrieval • synthetic evidence")
st.json(retrieve_spatial_evidence(repository=DemoRepository(),request_id="REQ-DEMO-082",query={"aoi_id":"DEMO-AOI"}))
