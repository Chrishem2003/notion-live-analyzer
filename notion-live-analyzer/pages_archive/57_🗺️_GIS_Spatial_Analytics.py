"""
Page 57 — GIS / QGIS-grade Spatial Analytics Engine
"""
import sys
from pathlib import Path

import streamlit as st

current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

st.set_page_config(page_title="GIS Spatial Analytics", page_icon="🗺️", layout="wide")

import pandas as pd  # noqa: E402


def _hero(title, subtitle, badge):
    st.markdown(
        f"""
        <div style="padding:1.6rem;background:linear-gradient(135deg,rgba(16,163,127,.12),rgba(11,19,33,.96));border-radius:14px;border:1px solid rgba(16,163,127,.35);margin-bottom:1.2rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;">
                <h1 style="color:#10b981 !important;font-size:1.9rem;margin:0;font-weight:800;">{title}</h1>
                <span style="background:rgba(16,163,127,.15);color:#10b981;padding:.3rem .8rem;border-radius:999px;font-size:.75rem;font-weight:700;border:1px solid #10b981;">{badge}</span>
            </div>
            <p style="color:#cbd5e1 !important;margin:.4rem 0 0;font-size:.95rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


_hero(
    "🗺️ GIS & QGIS-Grade Spatial Analytics Engine",
    "Full geospatial analysis suite: upload GeoJSON/Shapefile/KML, run vector operations (buffer, dissolve, spatial join, centroids), compute NDVI-style indices, render interactive choropleth maps, and export to GeoJSON/Shapefile/CSV.",
    "QGIS-Grade Enterprise Spatial Core",
)

try:
    from modules.gis_engine import render_gis_ui

    render_gis_ui()
except Exception as e:
    st.error(f"GIS engine failed to load: {e}")
    st.info("Ensure `geopandas`, `folium`, and `streamlit-folium` are installed for full functionality.")

st.markdown("---")
st.caption("CHRISHEM Multi-Problem Solver • GIS & Spatial Analytics Module")
