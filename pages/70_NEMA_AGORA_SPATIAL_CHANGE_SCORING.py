"""Phase 62 — NEMA-AGORA spatial change scoring demo."""
import streamlit as st
from nema_agora.spatial_change_scoring import score_candidate
st.set_page_config(page_title="NEMA-AGORA Change Scoring",layout="wide")
st.title("NEMA-AGORA — Spatial Change Evidence Scoring")
st.caption("Phase 62 • transparent engineering prioritisation")
candidate={"state":"CANDIDATE_CHANGE_DETECTED","candidate_id":"CHANGE-DEMO-001","fingerprint":"DEMO-CANDIDATE","spatial":{"baseline_aoi_id":"DEMO-WETLAND-01","comparison_aoi_id":"DEMO-WETLAND-01","spatial_alignment":"ALIGNED"},"change":{"NDVI":{"absolute_delta":0.20},"NDWI_MCFEETERS":{"absolute_delta":0.15}},"quality":{"baseline_cloud_cover_pct":8.0,"comparison_cloud_cover_pct":12.0,"baseline_valid_fraction":0.94,"comparison_valid_fraction":0.91},"uncertainty":{"ndvi_uncertainty":0.03,"ndwi_uncertainty":0.04},"reason_codes":["NDVI_CHANGE_THRESHOLD_MET","NDWI_CHANGE_THRESHOLD_MET","COMBINED_CHANGE_SIGNAL"]}
c1,c2=st.columns(2)
with c1: threshold=st.slider("Review threshold",0.0,1.0,0.5,0.01)
with c2: quality_weight=st.slider("Quality weight",0.0,1.0,0.0,0.05)
result=score_candidate(candidate=candidate,review_threshold=threshold,quality_weight=quality_weight)
st.metric("Priority tier",result.get("tier","CONTROL_REQUIRED"))
st.metric("Engineering score",result.get("score","—"))
st.json(result)
st.warning("This score prioritises human review only. It is not a probability, compliance score, environmental truth, NEMA authorisation, enforcement or emergency decision.")
