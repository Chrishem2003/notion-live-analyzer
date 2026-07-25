"""Page 41: Multi-Paper Meta-Analysis Matrix Synthesizer"""
import streamlit as st
from modules.meta_analysis_matrix import render_meta_analysis_matrix_ui

st.set_page_config(page_title="Meta-Analysis Matrix", page_icon="📑", layout="wide")
render_meta_analysis_matrix_ui()

