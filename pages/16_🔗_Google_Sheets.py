"""
🔗 Google Sheets Page — Read from and write to Google Sheets.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Google Sheets", layout="wide", page_icon="🔗")

from modules.page_setup import bootstrap_page, get_active_dataframe
from modules.google_sheets import render_google_sheets_ui

bootstrap_page("🔗 Google Sheets Integration", "Connect, read from, and write data to Google Sheets seamlessly.", "Cloud Sync")

active_df = get_active_dataframe(required=False)

render_google_sheets_ui(active_df)

