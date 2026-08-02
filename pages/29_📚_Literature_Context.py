"""
Automated Literature Context Page — Effect size comparison, citation suggestions, sample size benchmarking.
"""
import streamlit as st

st.set_page_config(page_title="Literature Context", page_icon="📚", layout="wide")

from modules.page_setup import require_dependency
from modules.literature_context import render_literature_context_ui

require_dependency("numpy", "⚠️ numpy required.")

render_literature_context_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Compare your effect sizes against field-specific benchmarks from large-scale meta-analyses. This helps contextualize your findings within the broader literature.")
