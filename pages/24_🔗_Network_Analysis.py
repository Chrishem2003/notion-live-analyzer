st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""
Network Analysis Page — Correlation networks, centrality, community detection.
"""
import streamlit as st

st.set_page_config(page_title="Network Analysis", page_icon="🔗", layout="wide")

from modules.network_analyzer import render_network_analysis_ui

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

if not HAS_NETWORKX:
    st.error("⚠️ networkx is required. Install with: `pip install networkx python-louvain`")
    st.stop()

render_network_analysis_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Network analysis reveals relationships between variables, papers, or research entities. Use centrality to identify key nodes.")
