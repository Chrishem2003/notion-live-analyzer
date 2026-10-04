import streamlit as st
from nema_agora.spatial_change_map import build_change_map
st.set_page_config(page_title="NEMA-AGORA Spatial Change Maps",layout="wide")
st.title("NEMA-AGORA — Spatial Change Maps")
st.warning("Synthetic grid demonstration; no live satellite pixels are connected.")
b={"NDVI":[[.7,.7],[.7,.7]],"NDWI_MCFEETERS":[[.3,.3],[.3,.3]],"MSAVI2":[[.65,.65],[.65,.65]]}
c={k:[row[:] for row in v] for k,v in b.items()};c["NDVI"][0][0]=.4
st.json(build_change_map(baseline_scene_id="DEMO-B",comparison_scene_id="DEMO-C",aoi_id="DEMO-AOI",baseline_indices=b,comparison_indices=c))