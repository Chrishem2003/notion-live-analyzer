"""
Natural Language Data Query Page — Ask questions about your data in plain English.
"""

import streamlit as st
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
st.set_page_config(page_title="NL Data Query", page_icon="💬", layout="wide")

from modules.nl_query_engine import render_nl_query_ui

try:
    import pandas as pd
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

if not HAS_DEPS:
    st.error("⚠️ pandas required.")
    st.stop()

df = st.session_state.get("active_df")
render_nl_query_ui(df)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Try 'describe data', 'compare [group] by [variable]', 'correlation between [col1] and [col2]', or 'missing values'.")
