"""Page 41: Multi-Paper Meta-Analysis Matrix Synthesizer"""

import streamlit as st

st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
from modules.meta_analysis_matrix import render_meta_analysis_matrix_ui

st.set_page_config(page_title="Meta-Analysis Matrix", page_icon="📑", layout="wide")
render_meta_analysis_matrix_ui()

