"""
🧬 Predictive Modeling Page — AutoML classification, regression, clustering, and forecasting.
"""

import streamlit as st
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
st.set_page_config(page_title="Predictive Modeling", layout="wide", page_icon="🧬")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark
from modules.predictive_engine import render_predictive_modeling_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("🧬 Predictive Modeling Engine", "Automated Machine Learning — Classification, Regression, Clustering, and Time Series Forecasting.", "AutoML Suite")
watermark("CHRISHEM")

active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ No data available. Load data from Notion, upload a file, or generate simulated data first.")
    st.stop()

render_predictive_modeling_ui(active_df)

