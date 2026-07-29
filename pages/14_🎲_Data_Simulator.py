"""
🎲 Data Simulator Page — Generate synthetic research data.
"""

import streamlit as st

st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
import pandas as pd

st.set_page_config(page_title="Data Simulator", layout="wide", page_icon="🎲")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header
from modules.data_simulator import render_data_simulator_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("🎲 Data Simulator", "Generate synthetic research datasets for teaching, testing, power analysis, and simulations.", "Data Generation")
watermark("CHRISHEM")

render_data_simulator_ui()

