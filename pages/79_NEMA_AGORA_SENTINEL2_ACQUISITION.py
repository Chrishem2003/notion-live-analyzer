import streamlit as st
from nema_agora.sentinel2_acquisition import build_acquisition_request,acquisition_boundary
st.set_page_config(page_title="NEMA-AGORA Sentinel-2 Acquisition",layout="wide")
st.title("NEMA-AGORA — Sentinel-2 Acquisition")
st.warning("Acquisition boundary only. No live Earth Engine credentials or satellite scenes are connected.")
g={"type":"Polygon","coordinates":[[[32,0],[32.1,0],[32.1,0.1],[32,0]]]}
r=build_acquisition_request("DEMO-REQ-071","DEMO-WETLAND-001",g,"COPERNICUS/S2_SR_HARMONIZED","2026-09-01","2026-10-01")
x=acquisition_boundary(r)
st.metric("Acquisition state",x["state"]);st.json(x)
