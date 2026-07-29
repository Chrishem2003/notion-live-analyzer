"""
📋 Methodology Advisor Page — Research design, test selection, and sample size estimation.
"""

import streamlit as st

st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
st.set_page_config(page_title="Methodology Advisor", layout="wide", page_icon="📋")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark
from modules.methodology_advisor import render_methodology_advisor_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("📋 Research Methodology Advisor", "Expert system for study design, statistical test selection, and sample size estimation.", "Research Methods")
watermark("CHRISHEM")

render_methodology_advisor_ui()

