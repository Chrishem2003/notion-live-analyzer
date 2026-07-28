"""Page 40: Real-Time Citation Integrity & Retraction Inspector"""
import streamlit as st
from modules.citation_inspector import render_citation_inspector_ui

st.set_page_config(page_title="Citation Inspector", page_icon="🚨", layout="wide")
render_citation_inspector_ui()

