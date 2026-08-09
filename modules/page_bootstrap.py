"""
Page Bootstrap Module
Handles global page configuration, layouts, and elite UI/UX styling injections across all pages.
"""

import streamlit as st

def inject_global_dropdown_fix():
    """Injects high-end enterprise dark-mode styling, smooth animations, and visible dropdown menus."""
    st.markdown("""
        <style>
            /* =========================================================================
               1. Global Theme & Premium Background Polish
               ========================================================================= */
            .stApp {
                background: radial-gradient(circle at top right, #0f172a 0%, #0b0f19 60%, #020617 100%);
                color: #f8fafc;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            /* Custom Scrollbar */
            ::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }
            ::-webkit-scrollbar-track {
                background: #0b0f19;
            }
            ::-webkit-scrollbar-thumb {
                background: #334155;
                border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #475569;
            }

            /* =========================================================================
               2. Crystal Clear Selectboxes & Dropdown Menus
               ========================================================================= */
            div[data-baseweb="select"] > div {
                background-color: #1e293b !important;
                border: 1px solid #334155 !important;
                color: #f8fafc !important;
                border-radius: 8px !important;
                transition: all 0.2s ease-in-out;
            }
            div[data-baseweb="select"] > div:hover {
                border-color: #38bdf8 !important;
                box-shadow: 0 0 10px rgba(56, 189, 248, 0.15);
            }
            
            /* Floating popover / dropdown options container */
            div[data-baseweb="popover"], div[data-baseweb="menu"], ul[data-baseweb="menu"] {
                background-color: #1e293b !important;
                border: 1px solid #475569 !important;
                border-radius: 10px !important;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.7), 0 10px 10px -5px rgba(0, 0, 0, 0.4) !important;
            }

            /* Individual items within the dropdown */
            div[data-baseweb="option"], li[data-baseweb="option"] {
                background-color: #1e293b !important;
                color: #e2e8f0 !important;
                border-radius: 6px !important;
                margin: 4px 6px !important;
                padding: 8px 12px !important;
                transition: background 0.15s ease;
            }

            /* Hover states for list items */
            div[data-baseweb="option"]:hover, li[data-baseweb="option"]:hover {
                background-color: #334155 !important;
                color: #ffffff !important;
            }

            /* Active / selected option highlight */
            div[data-baseweb="option"][aria-selected="true"], li[data-baseweb="option"][aria-selected="true"] {
                background-color: #0284c7 !important;
                color: #ffffff !important;
                font-weight: 600;
            }
            
            /* Multi-select chips/tags */
            span[data-baseweb="tag"] {
                background-color: #334155 !important;
                color: #38bdf8 !important;
                border-radius: 6px !important;
                border: 1px solid #475569 !important;
            }

            /* =========================================================================
               3. High-End Glassmorphism Cards & Containers
               ========================================================================= */
            div.element-container div.stExpander, div.stTabs {
                background: rgba(30, 41, 59, 0.45);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(51, 65, 85, 0.6);
                border-radius: 14px;
                padding: 6px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
            }
            
            /* Metric Cards Polish */
            div[data-testid="stMetric"] {
                background: linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.85) 100%);
                border: 1px solid rgba(51, 65, 85, 0.8);
                padding: 18px;
                border-radius: 14px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
                transition: transform 0.2s ease, border-color 0.2s ease;
            }
            div[data-testid="stMetric"]:hover {
                border-color: rgba(56, 189, 248, 0.4);
                transform: translateY(-2px);
            }

            /* Primary Buttons */
            button[kind="primary"] {
                background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
                border: none !important;
                color: white !important;
                font-weight: 600 !important;
                border-radius: 8px !important;
                box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35) !important;
                transition: all 0.2s ease !important;
            }
            button[kind="primary"]:hover {
                background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
                box-shadow: 0 6px 16px rgba(14, 165, 233, 0.5) !important;
            }
        </style>
    """, unsafe_allow_html=True)

def setup_page(page_title="App", page_icon="📊", initial_sidebar_state="expanded"):
    """Configures page layout, title, icon, and injects elite styling."""
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state=initial_sidebar_state
    )
    inject_global_dropdown_fix()

def render_standard_footer(module_name="ANALYTICS STUDIO"):
    """Renders a sleek, professional footer across application pages."""
    st.markdown("---")
    st.markdown(
        f"<p style='text-align: center; color: #64748b; font-size: 0.85rem; letter-spacing: 0.8px;'>"
        f"🔒 Enterprise Analytics Hub • Module: <b style='color: #94a3b8;'>{module_name}</b>"
        f"</p>",
        unsafe_allow_html=True
    )