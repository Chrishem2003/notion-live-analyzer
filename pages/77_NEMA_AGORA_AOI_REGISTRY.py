import streamlit as st
from nema_agora.aoi_registry import build_asset,validate_registry,query_assets
st.set_page_config(page_title="NEMA-AGORA AOI Registry",layout="wide")
st.title("NEMA-AGORA — AOI Registry & Environmental Asset Catalog")
st.warning("Synthetic demonstration only. No official boundary dataset is connected.")
g={"type":"Polygon","coordinates":[[[32,0],[32.1,0],[32.1,0.1],[32,0]]]}
assets=[build_asset("DEMO-WETLAND-001","Synthetic Wetland","WETLAND",g,"SYNTHETIC","DEMO-BOUNDARY-001")]
r=validate_registry(assets)
a,b,c=st.columns(3);a.metric("State",r["state"]);b.metric("Assets",r["asset_count"]);c.metric("Findings",len(r["findings"]))
st.json(query_assets(assets))
st.info("Authoritative boundaries require an approved source.")