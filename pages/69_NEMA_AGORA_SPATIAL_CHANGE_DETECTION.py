"""Phase 61 — NEMA-AGORA broader spatial change detection demo."""
import streamlit as st
from nema_agora.spatial_change_detection import detect_candidate

st.set_page_config(page_title="NEMA-AGORA Spatial Change Detection", layout="wide")
st.title("NEMA-AGORA — Spatial Change Detection")
st.caption("Phase 61 • deterministic candidate generation from quality-approved evidence")

quality = {
    "state": "CANDIDATE_CHANGE_EVIDENCE", "change_fingerprint": "DEMO-QUALITY-001",
    "spatial": {"baseline_aoi_id":"DEMO-WETLAND-01","comparison_aoi_id":"DEMO-WETLAND-01",
                "baseline_grid_id":"GRID-10M-001","comparison_grid_id":"GRID-10M-001",
                "spatial_alignment":"ALIGNED","spatial_resolution_m":10.0},
    "quality": {"baseline_cloud_cover_pct":8.0,"comparison_cloud_cover_pct":12.0,
                "baseline_valid_fraction":0.94,"comparison_valid_fraction":0.91},
    "uncertainty": {"ndvi_uncertainty":0.03,"ndwi_uncertainty":0.04,"method":"UPSTREAM_PROVIDED"},
    "change": {"NDVI":{"delta":-0.20,"absolute_delta":0.20},
               "NDWI_MCFEETERS":{"delta":0.15,"absolute_delta":0.15}},
    "interpretation": {"status":"HUMAN_REVIEW_REQUIRED"}
}
st.subheader("Detection policy")
c1,c2,c3 = st.columns(3)
with c1: ndvi_threshold = st.slider("Minimum |ΔNDVI|", 0.0, 1.0, 0.15, 0.01)
with c2: ndwi_threshold = st.slider("Minimum |ΔNDWI|", 0.0, 1.0, 0.10, 0.01)
with c3: mode = st.selectbox("Rule mode", ["ANY","ALL","WEIGHTED"])
result = detect_candidate(quality_evidence=quality, min_abs_ndvi_delta=ndvi_threshold,
                          min_abs_ndwi_delta=ndwi_threshold, rule_mode=mode)
st.metric("Detection state", result["state"])
st.json(result)
st.warning("Candidate detection is analytical evidence for human review only. It does not establish environmental truth, illegality, NEMA authorization, enforcement, emergency response or production approval.")
