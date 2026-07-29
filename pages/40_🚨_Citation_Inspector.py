st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""Page 40: Real-Time Citation Integrity & Retraction Inspector"""
import streamlit as st
from modules.citation_inspector import render_citation_inspector_ui

st.set_page_config(page_title="Citation Inspector", page_icon="🚨", layout="wide")
render_citation_inspector_ui()

