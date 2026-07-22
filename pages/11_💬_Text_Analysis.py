"""
💬 Text Analysis Page — Sentiment analysis, word clouds, frequency analysis.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Text Analysis", layout="wide", page_icon="💬")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark
from modules.text_analyzer import render_text_analysis_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("💬 Text & Qualitative Analysis", "Sentiment analysis, word clouds, word frequency, N-gram extraction, and keyword analysis.", "NLP Tools")
watermark("CHRISHEM")

active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ No data available. Load data first.")
    st.stop()

render_text_analysis_ui(active_df)

