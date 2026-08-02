"""
📊 Dashboard Builder Page — Interactive multi-chart dashboard creator.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard Builder", layout="wide", page_icon="📊")

from modules.page_setup import bootstrap_page, get_active_dataframe
from modules.dashboard_builder import render_dashboard_builder_ui

bootstrap_page("📊 Interactive Dashboard Builder", "Create custom multi-chart dashboards with global filters and cross-filtering.", "Dashboard Studio")

active_df = get_active_dataframe()

render_dashboard_builder_ui(active_df)

