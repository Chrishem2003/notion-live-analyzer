"""NEMA-AGORA Phase 60 — Spatial/Temporal Evidence Quality."""
import streamlit as st
from nema_agora.spatial_temporal_change import spatial_temporal_change_evidence
from nema_agora.spatial_temporal_quality import spatial_temporal_quality_evidence

st.set_page_config(page_title="NEMA-AGORA Evidence Quality", layout="wide")
st.title("NEMA-AGORA — Spatial/Temporal Evidence Quality")
st.caption("phase60-v1 • co-location, imagery quality and uncertainty gates")
change = spatial_temporal_change_evidence(
    baseline_scene_id="DEMO-S2-BASE", comparison_scene_id="DEMO-S2-COMP",
    baseline_acquired_at="2026-09-01T10:00:00Z", comparison_acquired_at="2026-10-01T10:00:00Z",
    baseline_indices={"NDVI": 0.70, "NDWI_MCFEETERS": 0.30},
    comparison_indices={"NDVI": 0.50, "NDWI_MCFEETERS": 0.45}, min_temporal_gap_days=7)
evidence = spatial_temporal_quality_evidence(
    change_evidence=change, baseline_aoi_id="DEMO-AOI-001", comparison_aoi_id="DEMO-AOI-001",
    baseline_grid_id="GRID-10M-001", comparison_grid_id="GRID-10M-001", spatial_alignment="ALIGNED",
    spatial_resolution_m=10.0, baseline_cloud_cover_pct=8.0, comparison_cloud_cover_pct=12.0,
    baseline_valid_fraction=0.94, comparison_valid_fraction=0.91, ndvi_uncertainty=0.03, ndwi_uncertainty=0.04)
st.metric("Quality state", evidence["state"])
st.metric("Spatial alignment", evidence.get("spatial", {}).get("spatial_alignment", "CONTROL_REQUIRED"))
st.json(evidence)
st.warning("Evidence-quality acceptance is an engineering gate for human review. It is not environmental truth, a regulatory finding, NEMA authorization, enforcement, emergency response, or production approval.")
