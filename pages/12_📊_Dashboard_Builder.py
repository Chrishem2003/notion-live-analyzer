"""
📊 Dashboard Builder Page — Interactive multi-chart dashboard creator.
"""

import streamlit as st
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
import pandas as pd

st.set_page_config(page_title="Dashboard Builder", layout="wide", page_icon="📊")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark
from modules.dashboard_builder import render_dashboard_builder_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("📊 Interactive Dashboard Builder", "Create custom multi-chart dashboards with global filters and cross-filtering.", "Dashboard Studio")
watermark("CHRISHEM")

active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ No data available. Load data first.")
    st.stop()

render_dashboard_builder_ui(active_df)

