import streamlit as st,tempfile,os
from nema_agora.spatial_evidence_storage import SpatialEvidenceStore
st.set_page_config(page_title="NEMA-AGORA Evidence Storage",layout="wide")
st.title("NEMA-AGORA — Spatial Evidence Storage & Query")
st.info("Synthetic storage demonstration. Historical evidence is append-only and read-only in this interface.")
with tempfile.NamedTemporaryFile(suffix=".db",delete=False) as f:path=f.name
s=SpatialEvidenceStore(path)
record={"record_id":"SPATIAL-HISTORY-DEMO","case_id":"SPATIAL-CASE-DEMO","candidate_id":"CHANGE-DEMO","observed_at":"2026-10-04T10:00:00+00:00","sequence":1,"previous_record_fingerprint":None,"case_fingerprint":"a"*64,"spatial_identity":{"aoi_id":"AOI-DEMO","grid_id":"GRID-10M"},"review_outcome":"CONFIRMED_CHANGE","provenance":{"queue_fingerprint":"b"*64},"record_fingerprint":"c"*64}
s.append(record);rows=s.list(case_id="SPATIAL-CASE-DEMO")
st.metric("Stored records",len(rows));st.json(rows)
os.unlink(path)
