"""
📋 Methodology Advisor Page — Research design, test selection, and sample size estimation.
"""
import streamlit as st

st.set_page_config(page_title="Methodology Advisor", layout="wide", page_icon="📋")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark
from modules.methodology_advisor import render_methodology_advisor_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("📋 Research Methodology Advisor", "Expert system for study design, statistical test selection, and sample size estimation.", "Research Methods")
watermark("CHRISHEM")

render_methodology_advisor_ui()

