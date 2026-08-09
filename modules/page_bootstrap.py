"""
Page Bootstrap Module
Handles global page configuration, layouts, and polished styling injections across all pages.
"""

import streamlit as st

def inject_global_dropdown_fix():
    """Injects premium dark-mode UI polish, glowing focus states, and visible dropdown option styling."""
    st.markdown("""
        <style>
            /* =========================================================================
               1. Global Theme & Background Polish
               ========================================================================= */
            .stApp {
                background-color: #0b0f19;
                color: #f8fafc;
                font-family: 'Inter', sans-serif;
            }

            /* =========================================================================
               2. Polished Dropdown & Selectbox Container Fixes
               ========================================================================= */
            div[data-baseweb="select"] > div {
                background-color: #1e293b !important;
                border: 1px solid #334155 !important;
                color: #f8fafc !important;
                border-radius: 8px !important;
            }
            div[data-baseweb="select"] > div:hover {
                border-color: #38bdf8 !important;
            }
            
            /* Floating popover/menu container for dropdowns */
            div[data-baseweb="popover"], div[data-baseweb="menu"], ul[data-baseweb="menu"] {
                background-color: #1e293b !important;
                border: 1px solid #334155 !important;
                border-radius: 8px !important;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5) !important;
            }

            /* Individual options inside the dropdown list */
            div[data-baseweb="option"], li[data-baseweb="option"] {
                background-color: #1e293b !important;
                color: #f8fafc !important;
                border-radius: 4px !important;
                margin: 2px 4px !important;
            }

            /* Hover state for dropdown options */
            div[data-baseweb="option"]:hover, li[data-baseweb="option"]:hover {
                background-color: #334155 !important;
                color: #ffffff !important;
            }

            /* Selected option highlight */
            div[data-baseweb="option"][aria-selected="true"], li[data-baseweb="option"][aria-selected="true"] {
                background-color: #0284c7 !important;
                color: #ffffff !important;
            }
            
            /* Multi-select tags */
            span[data-baseweb="tag"] {
                background-color: #334155 !important;
                color: #f8fafc !important;
                border-radius: 4px !important;
            }

            /* =========================================================================
               3. Modern Card & Container Layout Enhancements
               ========================================================================= */
            div.element-container div.stExpander, div.stTabs {
                background-color: rgba(30, 41, 59, 0.4);
                border: 1px solid rgba(51, 65, 85, 0.6);
                border-radius: 12px;
                padding: 4px;
            }
            
            /* Metric cards styling polish */
            div[data-testid="stMetric"] {
                background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
                border: 1px solid rgba(51, 65, 85, 0.8);
                padding: 16px;
                border-radius: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }
        </style>
    """, unsafe_allow_html=True)

def setup_page(page_title="App", page_icon="📊", initial_sidebar_state="expanded"):
    """Configures page layout, title, icon, and injects polished styling."""
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state=initial_sidebar_state
    )
    inject_global_dropdown_fix()

def render_standard_footer(module_name="ANALYTICS STUDIO"):
    """Renders a standardized, polished footer across application pages."""
    st.markdown("---")
    st.markdown(
        f"<p style='text-align: center; color: #64748b; font-size: 0.85rem; letter-spacing: 0.5px;'>"
        f"🔒 Enterprise Analytics Hub • Module: <b>{module_name}</b>"
        f"</p>",
        unsafe_allow_html=True
    )