import streamlit as st
from nema_agora.spatial_command_center import build_command_center
st.set_page_config(page_title="NEMA-AGORA Spatial Command Center",layout="wide")
st.title("NEMA-AGORA — Spatial Command Center")
st.info("Governed evidence view • synthetic demonstration • read-only")
m={"state":"MAP_READY","map_id":"MAP-DEMO","baseline_scene_id":"S2-BASE","comparison_scene_id":"S2-COMP","grid_shape":[2,2],"cells":[{"row":0,"col":0,"changed":True},{"row":0,"col":1,"changed":False},{"row":1,"col":0,"changed":True},{"row":1,"col":1,"changed":False}],"summary":{"changed_cells":2,"total_cells":4}}
st.json(build_command_center(aoi={"asset_id":"DEMO-AOI","name":"Synthetic AOI","asset_type":"CUSTOM"},change_map=m))
