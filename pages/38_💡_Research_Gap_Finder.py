"""Page 38: Novelty & Unexplored Research Gap Finder"""
import streamlit as st
from modules.research_gap_finder import render_research_gap_finder_ui

st.set_page_config(page_title="Research Gap Finder", page_icon="💡", layout="wide")
render_research_gap_finder_ui()

