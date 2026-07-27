"""
🛠️ Developer Console — restricted to admin accounts holding the panel password.
"""
import streamlit as st

st.set_page_config(page_title="Admin", layout="wide", page_icon="🛠️")

from modules.admin_console import render
from modules.config import init_session_state
from modules.session_auth import render_account_badge
from modules.ui_components import load_css, watermark

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
watermark("CHRISHEM")

with st.sidebar:
    render_account_badge()

render()
