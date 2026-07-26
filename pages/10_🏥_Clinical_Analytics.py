"""
🏥 Clinical Analytics Page — BMI calculator, clinical reference ranges, Z-scores, health risk.
"""
import streamlit as st

st.set_page_config(page_title="Clinical Analytics", layout="wide", page_icon="🏥")

from modules.page_setup import bootstrap_page
from modules.clinical_analytics import render_clinical_analytics_ui

bootstrap_page("🏥 Clinical & Health Analytics", "BMI calculator, clinical reference ranges, Z-scores, percentiles, and cardiovascular risk assessment.", "Health Metrics")

render_clinical_analytics_ui()

