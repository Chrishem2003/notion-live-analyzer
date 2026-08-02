"""
Network Analysis Page — Correlation networks, centrality, community detection.
"""
import streamlit as st

st.set_page_config(page_title="Network Analysis", page_icon="🔗", layout="wide")

from modules.page_setup import require_dependency
from modules.network_analyzer import render_network_analysis_ui

require_dependency("networkx", "⚠️ networkx is required. Install with: `pip install networkx python-louvain`")

render_network_analysis_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Network analysis reveals relationships between variables, papers, or research entities. Use centrality to identify key nodes.")
