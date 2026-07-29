"""
Automated Literature Context Page — Effect size comparison, citation suggestions, sample size benchmarking.
"""

import streamlit as st
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
st.set_page_config(page_title="Literature Context", page_icon="📚", layout="wide")

from modules.literature_context import render_literature_context_ui

try:
    import numpy as np
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

if not HAS_DEPS:
    st.error("⚠️ numpy required.")
    st.stop()

render_literature_context_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Compare your effect sizes against field-specific benchmarks from large-scale meta-analyses. This helps contextualize your findings within the broader literature.")
