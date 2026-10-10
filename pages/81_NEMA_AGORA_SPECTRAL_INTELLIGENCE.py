import streamlit as st
from nema_agora.spectral_indices import expanded_spectral_evidence
st.set_page_config(page_title="NEMA-AGORA Spectral Intelligence",layout="wide")
st.title("NEMA-AGORA — Expanded Spectral Intelligence")
st.warning("Synthetic reflectance demonstration. No live raster pixels are connected.")
x=expanded_spectral_evidence(scene_id="DEMO-S73",band_values={"B03":.60,"B04":.20,"B08":.80})
st.json(x)
