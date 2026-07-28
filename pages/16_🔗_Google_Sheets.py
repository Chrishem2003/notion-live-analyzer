"""
🔗 Google Sheets Page — Read from and write to Google Sheets.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Google Sheets", layout="wide", page_icon="🔗")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark
from modules.google_sheets import render_google_sheets_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("🔗 Google Sheets Integration", "Connect, read from, and write data to Google Sheets seamlessly.", "Cloud Sync")
watermark("CHRISHEM")

active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

render_google_sheets_ui(active_df)

