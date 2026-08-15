"""
Page Bootstrap Module
Handles global page configuration, layouts, and guaranteed dark sidebar styling across all pages.
"""

import streamlit as st

def inject_global_dropdown_fix():
    """Injects high-contrast typography, overrides sidebar white backgrounds, and fixes dropdowns."""
    st.markdown("""
        <style>
            /* =========================================================================
               1. Global Theme & Crystal Clear Typography
               ========================================================================= */
            .stApp {
                background: radial-gradient(circle at top right, #0f172a 0%, #0b0f19 60%, #020617 100%);
                color: #f1f5f9 !important;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            p, span, label, .stMarkdown, div[data-testid="stMarkdownContainer"] {
                color: #e2e8f0 !important;
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
                background: #475569;
                border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #64748b;
            }

            /* =========================================================================
               2. Full Sidebar Background & Navigation Overhaul (Fixes White Box)
               ========================================================================= */
            /* Force entire sidebar container to dark */
            section[data-testid="stSidebar"], 
            div[data-testid="stSidebarContent"], 
            div[data-testid="stSidebarUserContent"] {
                background-color: #090d16 !important;
                color: #f8fafc !important;
            }

            section[data-testid="stSidebar"] {
                border-right: 1px solid #1e293b !important;
            }

            /* Target the multi-page navigation container block */
            [data-testid="stSidebarNav"] {
                background-color: #090d16 !important;
            }

            /* Target individual sidebar navigation links and spans */
            [data-testid="stSidebarNav"] ul {
                background-color: #090d16 !important;
            }

            [data-testid="stSidebarNav"] li {
                background-color: transparent !important;
            }

            [data-testid="stSidebarNav"] a {
                background-color: transparent !important;
                color: #cbd5e1 !important;
                border-radius: 8px !important;
                margin: 3px 0px !important;
                padding: 10px 14px !important;
                transition: all 0.2s ease !important;
                border: 1px solid transparent !important;
            }

            /* Ensure all text/icons inside sidebar nav are bright white/slate */
            [data-testid="stSidebarNav"] a span, 
            [data-testid="stSidebarNav"] a div {
                color: #f8fafc !important;
                font-weight: 500 !important;
            }

            /* Sidebar navigation link hover state */
            [data-testid="stSidebarNav"] a:hover {
                background-color: #1e293b !important;
                border-color: #334155 !important;
                color: #ffffff !important;
            }

            /* Active sidebar page highlight */
            [data-testid="stSidebarNav"] a[aria-current="page"] {
                background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
                color: #ffffff !important;
                font-weight: 600 !important;
                box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3) !important;
            }

            /* =========================================================================
               3. Crystal Clear Selectboxes & Dropdown Menus
               ========================================================================= */
            div[data-baseweb="select"] > div {
                background-color: #1e293b !important;
                border: 1px solid #475569 !important;
                color: #ffffff !important;
                border-radius: 8px !important;
                font-weight: 500 !important;
            }
            div[data-baseweb="select"] > div:hover {
                border-color: #38bdf8 !important;
                box-shadow: 0 0 12px rgba(56, 189, 248, 0.2);
            }
            
            div[data-baseweb="select"] span {
                color: #ffffff !important;
            }
            
            div[data-baseweb="popover"], div[data-baseweb="menu"], ul[data-baseweb="menu"] {
                background-color: #1e293b !important;
                border: 1px solid #64748b !important;
                border-radius: 10px !important;
                box-shadow: 0 20px 30px -5px rgba(0, 0, 0, 0.8) !important;
            }

            div[data-baseweb="option"], li[data-baseweb="option"] {
                background-color: #1e293b !important;
                color: #f8fafc !important;
                border-radius: 6px !important;
                margin: 4px 6px !important;
                padding: 10px 14px !important;
                font-weight: 500 !important;
            }

            div[data-baseweb="option"]:hover, li[data-baseweb="option"]:hover {
                background-color: #334155 !important;
                color: #ffffff !important;
            }

            div[data-baseweb="option"][aria-selected="true"], li[data-baseweb="option"][aria-selected="true"] {
                background-color: #0284c7 !important;
                color: #ffffff !important;
                font-weight: 700 !important;
            }

            /* =========================================================================
               4. Glassmorphism Containers & Metrics Polish
               ========================================================================= */
            div.element-container div.stExpander, div.stTabs {
                background: rgba(30, 41, 59, 0.5);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(71, 85, 105, 0.6);
                border-radius: 14px;
                padding: 8px;
            }
            
            div[data-testid="stMetric"] {
                background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
                border: 1px solid rgba(71, 85, 105, 0.8);
                padding: 18px;
                border-radius: 14px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
            }
            div[data-testid="stMetricLabel"] label {
                color: #cbd5e1 !important;
                font-weight: 600 !important;
            }
            div[data-testid="stMetricValue"] {
                color: #38bdf8 !important;
                font-weight: 700 !important;
            }
        </style>
    """, unsafe_allow_html=True)

def setup_page(page_title="App", page_icon="📊", initial_sidebar_state="expanded"):
    """Configures page layout, title, icon, and injects dark sidebar styling."""
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state=initial_sidebar_state
    )
    inject_global_dropdown_fix()

def render_standard_footer(module_name="ANALYTICS STUDIO"):
    """Renders a sleek, crisp footer across application pages."""
    st.markdown("---")
    st.markdown(
        f"<p style='text-align: center; color: #94a3b8; font-size: 0.85rem; letter-spacing: 0.8px;'>"
        f"🔒 Enterprise Analytics Hub • Module: <b style='color: #f8fafc;'>{module_name}</b>"
        f"</p>",
        unsafe_allow_html=True
    )