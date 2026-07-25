"""Page 37: Visual Chart Data Extractor & CSV Re-Synthesizer"""
import streamlit as st
from modules.chart_data_extractor import render_chart_data_extractor_ui

st.set_page_config(page_title="Chart Data Extractor", page_icon="📊", layout="wide")
render_chart_data_extractor_ui()

