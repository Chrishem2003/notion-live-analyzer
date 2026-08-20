import streamlit as st

def setup_page(title="Notion Live Analyzer", icon="🚀", layout="wide"):
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout=layout,
        initial_sidebar_state="expanded"
    )

def render_standard_footer():
    st.markdown("---")
    st.caption("⚡ **Chrishem Sovereign Apex Hub** | Powered by Notion Live Analyzer")
