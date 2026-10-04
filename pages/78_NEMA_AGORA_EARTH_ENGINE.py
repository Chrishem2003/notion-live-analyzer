import streamlit as st
from nema_agora.earth_engine import build_request,provider_boundary
st.set_page_config(page_title="NEMA-AGORA Earth Engine",layout="wide")
st.title("NEMA-AGORA — Google Earth Engine Boundary")
st.warning("Integration boundary only. No live Earth Engine credentials or environmental data are connected.")
g={"type":"Polygon","coordinates":[[[32,0],[32.1,0],[32.1,0.1],[32,0]]]}
r=build_request("DEMO-REQ-001","DEMO-WETLAND-001",g,"COPERNICUS/S2_SR_HARMONIZED","2026-09-01","2026-10-01")
x=provider_boundary(r)
st.metric("Provider state",x["state"]);st.json(x)
