"""
🧬 Predictive Modeling Page — AutoML classification, regression, clustering, and forecasting.
"""
import streamlit as st

st.set_page_config(page_title="Predictive Modeling", layout="wide", page_icon="🧬")

from modules.page_setup import bootstrap_page, get_active_dataframe
from modules.predictive_engine import render_predictive_modeling_ui

bootstrap_page("🧬 Predictive Modeling Engine", "Automated Machine Learning — Classification, Regression, Clustering, and Time Series Forecasting.", "AutoML Suite")

active_df = get_active_dataframe(warning="⚠️ No data available. Load data from Notion, upload a file, or generate simulated data first.")

render_predictive_modeling_ui(active_df)

