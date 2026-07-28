"""
🔍 Data Quality Page — Automated data quality assessment and reporting.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Data Quality", layout="wide", page_icon="🔍")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark
from modules.data_quality import render_data_quality_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("🔍 Data Quality Assessment", "Automated data quality audit — completeness, uniqueness, consistency, validity, and accuracy.", "Data Audit")
watermark("CHRISHEM")

active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ No data available. Load data first.")
    st.stop()

render_data_quality_ui(active_df)

