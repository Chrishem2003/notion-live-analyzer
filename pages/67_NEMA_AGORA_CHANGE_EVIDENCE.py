"""NEMA-AGORA Phase 59 — Spatial/Temporal Change Evidence."""
import streamlit as st
from nema_agora.spatial_temporal_change import spatial_temporal_change_evidence

st.set_page_config(page_title="NEMA-AGORA Change Evidence", layout="wide")
st.title("NEMA-AGORA — Spatial/Temporal Change Evidence")
st.caption("phase59-v1 • synthetic Sentinel-2-derived observations • human-review evidence")
evidence=spatial_temporal_change_evidence(
    baseline_scene_id="DEMO-S2-BASE", comparison_scene_id="DEMO-S2-COMP",
    baseline_acquired_at="2026-09-01T10:00:00Z", comparison_acquired_at="2026-10-01T10:00:00Z",
    baseline_indices={"NDVI":0.70,"NDWI_MCFEETERS":0.30},
    comparison_indices={"NDVI":0.50,"NDWI_MCFEETERS":0.45},
    min_temporal_gap_days=7,
    quality={"imagery_inputs":"metadata_validated","spatial_alignment":"synthetic_demo"})
st.metric("Evidence state", evidence["state"])
for name,change in evidence.get("change",{}).items():
    st.metric(name, f"{change['delta']:+.4f}", f"|delta| {change['absolute_delta']:.4f}")
st.subheader("Evidence package")
st.json(evidence)
st.warning("Candidate change is not a regulatory finding. Human review, spatial alignment, seasonality/context and quality assessment are required.")
