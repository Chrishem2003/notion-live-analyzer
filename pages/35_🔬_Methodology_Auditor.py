"""Page 35: Active Bias & Methodological Flaw Detector"""
import streamlit as st
from modules.methodology_auditor import render_methodology_auditor_ui

st.set_page_config(page_title="Methodology Auditor", page_icon="🔬", layout="wide")
render_methodology_auditor_ui()

