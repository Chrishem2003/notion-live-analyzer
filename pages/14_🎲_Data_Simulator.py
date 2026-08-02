"""
🎲 Data Simulator Page — Generate synthetic research data.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Data Simulator", layout="wide", page_icon="🎲")

from modules.page_setup import bootstrap_page
from modules.ui_components import section_header
from modules.data_simulator import render_data_simulator_ui

bootstrap_page("🎲 Data Simulator", "Generate synthetic research datasets for teaching, testing, power analysis, and simulations.", "Data Generation")

render_data_simulator_ui()

