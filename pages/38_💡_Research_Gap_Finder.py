"""Page 38: Novelty & Unexplored Research Gap Finder"""

import streamlit as st

st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
from modules.research_gap_finder import render_research_gap_finder_ui

st.set_page_config(page_title="Research Gap Finder", page_icon="💡", layout="wide")
render_research_gap_finder_ui()

