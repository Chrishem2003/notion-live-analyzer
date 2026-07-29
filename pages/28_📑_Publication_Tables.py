"""
Publication-Ready Tables Page — APA-style tables, correlation matrices, regression tables.
"""

import streamlit as st

st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
st.set_page_config(page_title="Publication Tables", page_icon="📑", layout="wide")

from modules.table_generator import render_table_generator_ui

try:
    import pandas as pd
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

if not HAS_DEPS:
    st.error("⚠️ pandas required.")
    st.stop()

render_table_generator_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** APA 7th edition requires effect sizes and confidence intervals for all statistical tests. Use these tables to generate publication-ready output.")
