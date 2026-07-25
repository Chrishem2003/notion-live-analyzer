"""Page 46: Application Pipeline, Document Vault & Currency Module"""
import streamlit as st
from modules.application_pipeline import render_pipeline_ui

st.set_page_config(
    page_title="Application Pipeline & Document Vault",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)
render_pipeline_ui()

