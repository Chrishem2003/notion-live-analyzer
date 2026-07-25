"""Page 43: One-Click Grant & Journal Transpiler"""
import streamlit as st
from modules.grant_formatter import render_grant_formatter_ui

st.set_page_config(page_title="Grant & Journal Transpiler", page_icon="📜", layout="wide")
render_grant_formatter_ui()

