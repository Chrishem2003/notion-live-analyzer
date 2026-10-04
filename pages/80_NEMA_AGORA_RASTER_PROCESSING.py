import streamlit as st
from nema_agora.raster_processing import build_raster_input,process_raster
st.set_page_config(page_title="NEMA-AGORA Raster Processing",layout="wide")
st.title("NEMA-AGORA — Raster Processing Pipeline")
st.warning("Processing contract demonstration. No live raster pixels are connected.")
g={"type":"Polygon","coordinates":[[[32,0],[32.1,0],[32.1,0.1],[32,0]]]}
b=[{"band_id":f"B-{x}","band":x,"width":100,"height":100,"dtype":"uint16","resolution_m":10} for x in ("B02","B03","B04","B08")]
r=build_raster_input("DEMO-SCENE-072",g,b,valid_fraction=.95,cloud_mask_applied=True)
st.json(process_raster(r))
