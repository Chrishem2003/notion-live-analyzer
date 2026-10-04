"""NEMA-AGORA Phase 56 — Spatial Intelligence Foundation."""
import streamlit as st
from nema_agora.spatial_intelligence import POLICY_VERSION, aoi, spatial_analysis_contract, spatial_observation, validate_aoi, validate_spatial_observation

st.set_page_config(page_title="NEMA-AGORA Spatial Intelligence", layout="wide")
st.title("NEMA-AGORA — Spatial Intelligence Foundation")
st.caption(f"{POLICY_VERSION} • provider-neutral spatial contracts")
obs = spatial_observation("DEMO-SPATIAL-001", 0.3476, 32.5825, "synthetic-demo", "2026-10-04T12:00:00Z", accuracy_m=10)
demo_aoi = aoi("AOI-DEMO-001", "Demo Wetland Area", "WETLAND", {"type":"Point","coordinates":[32.5825,0.3476]})
st.metric("Observation", validate_spatial_observation(obs)["state"])
st.metric("AOI", validate_aoi(demo_aoi)["state"])
st.json({"observation": obs, "aoi": demo_aoi})
st.subheader("Provider contract")
st.json(spatial_analysis_contract({"provider":"synthetic-demo","analysis_type":"change_candidate","source_ids":["DEMO-SPATIAL-001"],"evidence":{"status":"candidate"},"confidence":0.5,"metadata":{"synthetic":True}}))
st.warning("Spatial analytics are evidence for human review. They do not establish illegality, environmental truth, regulatory status, enforcement action, emergency response, or NEMA authorization.")
