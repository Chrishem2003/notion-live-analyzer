"""
🔗 Google Sheets Page — Read from and write to Google Sheets.
"""

import streamlit as st

st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
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

