"""
💬 Text Analysis Page — Sentiment analysis, word clouds, frequency analysis.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Text Analysis", layout="wide", page_icon="💬")

from modules.page_setup import bootstrap_page, get_active_dataframe
from modules.text_analyzer import render_text_analysis_ui

bootstrap_page("💬 Text & Qualitative Analysis", "Sentiment analysis, word clouds, word frequency, N-gram extraction, and keyword analysis.", "NLP Tools")

active_df = get_active_dataframe()

render_text_analysis_ui(active_df)

