"""
🏥 Clinical Analytics Page — BMI calculator, clinical reference ranges, Z-scores, health risk.
"""
import streamlit as st

st.set_page_config(page_title="Clinical Analytics", layout="wide", page_icon="🏥")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark
from modules.clinical_analytics import render_clinical_analytics_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("🏥 Clinical & Health Analytics", "BMI calculator, clinical reference ranges, Z-scores, percentiles, and cardiovascular risk assessment.", "Health Metrics")
watermark("CHRISHEM")

render_clinical_analytics_ui()

