"""NEMA-AGORA Phase 58 — NDVI / McFeeters NDWI."""
import streamlit as st

from nema_agora.spectral_indices import (
    POLICY_VERSION,
    spectral_index_evidence,
    validate_spectral_inputs,
)

st.set_page_config(page_title="NEMA-AGORA NDVI / NDWI", layout="wide")
st.title("NEMA-AGORA — NDVI / NDWI Analytics")
st.caption(f"{POLICY_VERSION} • transparent spectral-index engine • synthetic demonstration")

scene_id = "DEMO-S2-SCENE"
bands = {"B03": 0.60, "B04": 0.20, "B08": 0.80}

validation = validate_spectral_inputs(scene_id=scene_id, band_values=bands)
evidence = spectral_index_evidence(scene_id=scene_id, band_values=bands)

col1, col2 = st.columns(2)
with col1:
    st.metric("Input validation", validation["state"])
with col2:
    st.metric("Evidence state", evidence["state"])

st.subheader("Normalized reflectance inputs")
st.json(bands)

st.subheader("Computed indices")
for name, value in evidence.get("index_values", {}).items():
    st.metric(name, f"{value:.4f}")

st.subheader("Transparent evidence contract")
st.json(evidence)

st.info(
    "NDVI/NDWI values are analytical measurements. They do not by themselves establish "
    "deforestation, wetland loss, illegality, regulatory status, enforcement action, "
    "emergency response, or NEMA authorization. Human review and appropriate spatial/temporal "
    "comparison are required before interpreting change."
)
