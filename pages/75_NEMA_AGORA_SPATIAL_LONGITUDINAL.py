import streamlit as st
from nema_agora.spatial_evidence_longitudinal import build_longitudinal_record,build_timeline
st.set_page_config(page_title="NEMA-AGORA Spatial Longitudinal Evidence",layout="wide")
st.title("NEMA-AGORA — Spatial Evidence Longitudinal Tracking")
case={"case_id":"SPATIAL-CASE-DEMO","candidate_id":"CHANGE-DEMO","case_fingerprint":"a"*64,"queue_artifact":{"spatial":{"aoi_id":"AOI-DEMO","grid_id":"GRID-10M"}},"review_outcome":"CONFIRMED_CHANGE","provenance":{"queue_fingerprint":"b"*64,"audit_event_fingerprint":"c"*64,"reconciliation_fingerprint":"d"*64}}
a=build_longitudinal_record(case,observed_at="2026-10-04T10:00:00+00:00",sequence=1)["record"]
b=build_longitudinal_record(case,observed_at="2026-10-05T10:00:00+00:00",sequence=2,previous_record_fingerprint=a["record_fingerprint"])["record"]
t=build_timeline([a,b])
x,y,z=st.columns(3);x.metric("State",t["state"]);y.metric("History records",len(t["records"]));z.metric("Findings",len(t["findings"]))
st.json(t)
st.info("Immutable evidence history only; no environmental or regulatory conclusion is produced.")
