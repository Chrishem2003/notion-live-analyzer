import streamlit as st
from nema_agora.spatial_map_layers import build_map_layers
st.set_page_config(page_title="NEMA-AGORA Spatial Map Layers",layout="wide")
st.title("NEMA-AGORA — Spatial Evidence Map Layers")
st.info("Governed visualization contract • synthetic demonstration • read-only")
m={"state":"MAP_READY","map_id":"MAP-DEMO","baseline_scene_id":"S2-BASE","comparison_scene_id":"S2-COMP","cells":[{"row":0,"col":0,"changed":True,"reason_codes":["NDVI_CHANGE_THRESHOLD_MET"]},{"row":0,"col":1,"changed":False,"reason_codes":[]}]}
st.json(build_map_layers(aoi={"asset_id":"DEMO-AOI"},change_map=m,priority_items=[]))
