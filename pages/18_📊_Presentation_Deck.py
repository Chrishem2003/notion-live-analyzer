"""
📊 Presentation Deck Builder Page — Compile charts, insights, and data
into an interactive presentation deck view with export.
"""
import streamlit as st

st.set_page_config(page_title="Presentation Deck", layout="wide", page_icon="📊")

from modules.page_setup import bootstrap_page
from modules.ui_components import section_header
from modules.deck_builder import render_deck_builder_ui

bootstrap_page(
    "📊 Presentation Deck Builder",
    "Compile charts, AI insights, statistical results, and data tables into an interactive presentation deck. Export as HTML or PDF.",
    "Deck Builder"
)

render_deck_builder_ui()

