"""
🔗 Git Integration Page — Connect GitHub for data version control,
script pushing, and collaborative analysis.
"""
import streamlit as st

st.set_page_config(page_title="Git Integration", layout="wide", page_icon="🔗")

from modules.config import init_session_state
from modules.ui_components import hero_card, section_header, load_css, watermark, git_status_badge
from modules.git_integration import render_git_integration_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

is_connected = st.session_state.get("git_connected", False)
badge = git_status_badge(is_connected)

hero_card(
    "🔗 Git Repository Integration",
    f"Connect your GitHub repository for data version control, analysis script sharing, and collaborative research. {badge}",
    "Git & Version Control"
)
watermark("CHRISHEM")

render_git_integration_ui()

