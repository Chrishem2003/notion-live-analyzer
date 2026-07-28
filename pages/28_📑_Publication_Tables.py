"""
Publication-Ready Tables Page — APA-style tables, correlation matrices, regression tables.
"""
import streamlit as st

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
