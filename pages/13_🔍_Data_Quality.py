"""
🔍 Data Quality Page — Automated data quality assessment and reporting.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Data Quality", layout="wide", page_icon="🔍")

from modules.page_setup import bootstrap_page, get_active_dataframe
from modules.data_quality import render_data_quality_ui

bootstrap_page("🔍 Data Quality Assessment", "Automated data quality audit — completeness, uniqueness, consistency, validity, and accuracy.", "Data Audit")

active_df = get_active_dataframe()

render_data_quality_ui(active_df)

