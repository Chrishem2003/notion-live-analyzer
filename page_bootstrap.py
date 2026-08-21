"""
Page Bootstrap Module
Handles global page configuration, layout, and shared styling across all pages.
Colors are driven by theme.get_theme() so dark/light mode actually applies
everywhere instead of being hardcoded per-page.
"""

import streamlit as st
from theme import get_theme, inject_global_css, render_theme_toggle


def inject_global_dropdown_fix():
    """Extra high-contrast styling for dropdowns, sidebar nav, and metric
    cards, layered on top of theme.inject_global_css(). Uses live theme
    colors so it respects the active dark/light mode instead of forcing dark."""
    t = get_theme()
    st.markdown(f"""
        <style>
            /* Custom Scrollbar */
            ::-webkit-scrollbar {{
                width: 8px;
                height: 8px;
            }}
            ::-webkit-scrollbar-track {{
                background: {t['bg_secondary']};
            }}
            ::-webkit-scrollbar-thumb {{
                background: {t['border']};
                border-radius: 4px;
            }}
            ::-webkit-scrollbar-thumb:hover {{
                background: {t['text_muted']};
            }}

            /* Sidebar Navigation */
            [data-testid="stSidebarNav"] a {{
                background-color: transparent !important;
                color: {t['text_secondary']} !important;
                border-radius: 8px !important;
                margin: 3px 0px !important;
                padding: 10px 14px !important;
                transition: all 0.2s ease !important;
                border: 1px solid transparent !important;
            }}

            [data-testid="stSidebarNav"] a span,
            [data-testid="stSidebarNav"] a div {{
                color: {t['text_primary']} !important;
                font-weight: 500 !important;
            }}

            [data-testid="stSidebarNav"] a:hover {{
                background-color: {t['bg_card']} !important;
                border-color: {t['border']} !important;
            }}

            [data-testid="stSidebarNav"] a[aria-current="page"] {{
                background: linear-gradient(135deg, {t['accent']} 0%, {t['accent_alt']} 100%) !important;
                color: {t['bg_primary']} !important;
                font-weight: 600 !important;
                box-shadow: 0 4px 12px {t['accent']}4d !important;
            }}

            /* Crystal Clear Selectboxes & Dropdown Menus */
            div[data-baseweb="select"] > div {{
                background-color: {t['bg_card']} !important;
                border: 1px solid {t['border']} !important;
                color: {t['text_primary']} !important;
                border-radius: 8px !important;
                font-weight: 500 !important;
            }}
            div[data-baseweb="select"] > div:hover {{
                border-color: {t['accent_alt']} !important;
                box-shadow: 0 0 12px {t['accent_alt']}33;
            }}

            div[data-baseweb="select"] span {{
                color: {t['text_primary']} !important;
            }}

            div[data-baseweb="popover"], div[data-baseweb="menu"], ul[data-baseweb="menu"] {{
                background-color: {t['bg_card']} !important;
                border: 1px solid {t['border']} !important;
                border-radius: 10px !important;
                box-shadow: 0 20px 30px -5px rgba(0, 0, 0, 0.4) !important;
            }}

            div[data-baseweb="option"], li[data-baseweb="option"] {{
                background-color: {t['bg_card']} !important;
                color: {t['text_primary']} !important;
                border-radius: 6px !important;
                margin: 4px 6px !important;
                padding: 10px 14px !important;
                font-weight: 500 !important;
            }}

            div[data-baseweb="option"]:hover, li[data-baseweb="option"]:hover {{
                background-color: {t['border']} !important;
                color: {t['text_primary']} !important;
            }}

            div[data-baseweb="option"][aria-selected="true"], li[data-baseweb="option"][aria-selected="true"] {{
                background-color: {t['accent']} !important;
                color: {t['bg_primary']} !important;
                font-weight: 700 !important;
            }}

            /* Glassmorphism Containers & Metrics Polish */
            div.element-container div.stExpander, div.stTabs {{
                background: {t['bg_card']}80;
                backdrop-filter: blur(12px);
                border: 1px solid {t['border']}99;
                border-radius: 14px;
                padding: 8px;
            }}

            div[data-testid="stMetric"] {{
                background: linear-gradient(135deg, {t['bg_card']}cc 0%, {t['bg_secondary']}e6 100%);
                border: 1px solid {t['border']}cc;
                padding: 18px;
                border-radius: 14px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.15);
            }}
            div[data-testid="stMetricLabel"] label {{
                color: {t['text_secondary']} !important;
                font-weight: 600 !important;
            }}
            div[data-testid="stMetricValue"] {{
                color: {t['accent_alt']} !important;
                font-weight: 700 !important;
            }}
        </style>
    """, unsafe_allow_html=True)


def setup_page(page_title="App", page_icon="📊", initial_sidebar_state="expanded"):
    """Configures page layout/title/icon and injects theme-aware styling
    plus a working dark/light toggle. Call once near the top of every page."""
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state=initial_sidebar_state,
    )
    inject_global_css()
    inject_global_dropdown_fix()
    with st.sidebar:
        render_theme_toggle()


def render_standard_footer(module_name="ANALYTICS STUDIO"):
    """Renders a sleek, crisp footer across application pages."""
    t = get_theme()
    st.markdown("---")
    st.markdown(
        f"<p style='text-align: center; color: {t['text_muted']}; font-size: 0.85rem; letter-spacing: 0.8px;'>"
        f"🔒 Enterprise Analytics Hub • Module: <b style='color: {t['text_primary']};'>{module_name}</b>"
        f"</p>",
        unsafe_allow_html=True,
    )
