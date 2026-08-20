import streamlit as st

def setup_page(title="Notion Live Analyzer", icon="🚀", layout="wide"):
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout=layout,
        initial_sidebar_state="expanded"
    )
    
    # Custom Theme and UI Styling
    st.markdown("""
        <style>
        .main {
            background-color: #0f172a;
            color: #f8fafc;
        }
        .stSidebar {
            background-color: #1e293b;
        }
        div[data-testid="stMetricValue"] {
            color: #00adb5;
        }
        </style>
    """, unsafe_allow_html=True)

def render_standard_footer():
    st.markdown("---")
    st.caption("⚡ **Chrishem Sovereign Apex Hub** | Powered by Notion Live Analyzer")
