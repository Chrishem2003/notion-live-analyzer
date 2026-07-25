"""Page 44: Secure Personal Vault — Zero-Knowledge Encrypted Storage"""
import streamlit as st
from modules.secure_personal_vault import render_secure_vault_ui

st.set_page_config(
    page_title="Secure Personal Vault",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)
render_secure_vault_ui()

