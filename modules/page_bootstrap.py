"""
CHRISHEM Page Bootstrap — standardized setup for every consolidated hub page.
Injects the unified theme, initializes session state, renders sidebar navigation,
and provides a standard page scaffold.
"""

import streamlit as st

from modules.theme import inject_global_css
from modules.session_manager import init_session, render_sidebar_data_hud
from modules.navigation import (
    render_sidebar_navigation,
    render_global_command_search,
    render_sidebar_footer,
    visible_hubs,
)
from modules.shared_ui import render_footer


def setup_page(page_title: str, page_icon: str, initial_sidebar_state: str = "expanded"):
    """
    Perform the standardized page setup:
    1. Page config
    2. Session state initialization
    3. Global CSS injection
    4. Sidebar navigation + dataset HUD + command search
    Returns the selected hub dict.
    """
    st.set_page_config(
        page_title=f"{page_title} | CHRISHEM Unified Platform",
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state=initial_sidebar_state,
    )

    init_session()
    inject_global_css()

    # Sidebar: app brand
    st.sidebar.markdown("### ⚡ CHRISHEM")
    st.sidebar.caption("Sovereign Enterprise Engine v9.0")
    st.sidebar.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)

    # User identity quick panel
    identity = st.session_state.get("user_identity", {})
    st.sidebar.markdown(f"**👤 {identity.get('name', 'Analyst')}**")
    st.sidebar.caption(f"Role: {identity.get('role', 'Data Analyst')}")

    # Navigation
    selected_hub = render_sidebar_navigation()

    # Dataset HUD
    render_sidebar_data_hud()

    # Command search
    render_global_command_search()

    # Footer
    render_sidebar_footer()

    return selected_hub


def render_standard_footer(hub_name: str):
    """Render the standard hub footer."""
    render_footer(hub_name, version="9.0")


def hub_tool_label(hub_name: str, tool_name: str):
    """Return a standardized section header string."""
    return f"{hub_name} → {tool_name}"

# Global CSS Fix for Streamlit Selectboxes and Dropdown Options
def inject_global_dropdown_fix():
    import streamlit as st
    st.markdown("""
        <style>
            /* Fix Streamlit dropdown options background and text contrast */
            div[data-baseweb="select"] > div {
                background-color: #1e293b !important;
                color: #f8fafc !important;
            }
            ul[data-baseweb="menu"] {
                background-color: #1e293b !important;
            }
            li[data-baseweb="option"] {
                background-color: #1e293b !important;
                color: #f8fafc !important;
            }
            li[data-baseweb="option"]:hover {
                background-color: #334155 !important;
                color: #ffffff !important;
            }
            span[data-baseweb="tag"] {
                background-color: #334155 !important;
                color: #f8fafc !important;
            }
        </style>
    """, unsafe_allow_html=True)

