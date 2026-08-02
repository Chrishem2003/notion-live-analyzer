"""
📋 Methodology Advisor Page — Research design, test selection, and sample size estimation.
"""
import streamlit as st

st.set_page_config(page_title="Methodology Advisor", layout="wide", page_icon="📋")

from modules.page_setup import bootstrap_page
from modules.methodology_advisor import render_methodology_advisor_ui

bootstrap_page("📋 Research Methodology Advisor", "Expert system for study design, statistical test selection, and sample size estimation.", "Research Methods")

render_methodology_advisor_ui()

