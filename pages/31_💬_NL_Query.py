"""
Natural Language Data Query Page — Ask questions about your data in plain English.
"""
import streamlit as st

st.set_page_config(page_title="NL Data Query", page_icon="💬", layout="wide")

from modules.page_setup import require_dependency
from modules.nl_query_engine import render_nl_query_ui

require_dependency("pandas", "⚠️ pandas required.")

df = st.session_state.get("active_df")
render_nl_query_ui(df)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Try 'describe data', 'compare [group] by [variable]', 'correlation between [col1] and [col2]', or 'missing values'.")
