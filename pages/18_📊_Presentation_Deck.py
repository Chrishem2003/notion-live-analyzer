"""
📊 Presentation Deck Builder Page — Compile charts, insights, and data
into an interactive presentation deck view with export.
"""
import streamlit as st

st.set_page_config(page_title="Presentation Deck", layout="wide", page_icon="📊")

from modules.config import init_session_state
from modules.ui_components import hero_card, section_header, load_css, watermark
from modules.deck_builder import render_deck_builder_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "📊 Presentation Deck Builder",
    "Compile charts, AI insights, statistical results, and data tables into an interactive presentation deck. Export as HTML or PDF.",
    "Deck Builder"
)
watermark("CHRISHEM")

render_deck_builder_ui()

