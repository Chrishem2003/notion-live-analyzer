"""
📑 APA Outputs Page — Publication-ready APA 7th edition formatted results.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="APA Outputs", layout="wide", page_icon="📑")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark
from modules.apa_formatter import render_apa_outputs_page, render_apa_quick_format_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("📑 APA 7th Edition Results", "Publication-ready statistical reporting with professional formatting.", "APA Style")
watermark("CHRISHEM")

# Collect results from session state
statistical_results = st.session_state.get("statistical_results", [])

tab1, tab2 = st.tabs(["📄 Formatted Results", "🔧 Quick APA Formatter"])

with tab1:
    render_apa_outputs_page(statistical_results if statistical_results else None)

with tab2:
    render_apa_quick_format_ui()

