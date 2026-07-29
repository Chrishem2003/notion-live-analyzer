"""Page 44: Secure Personal Vault — Zero-Knowledge Encrypted Storage"""

import streamlit as st

st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
from modules.secure_personal_vault import render_secure_vault_ui

st.set_page_config(
    page_title="Secure Personal Vault",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)
render_secure_vault_ui()

