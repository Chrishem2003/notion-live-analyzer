import security_guard

import streamlit as st
from datetime import datetime
import zoneinfo

def render_ui_enhancements():
    try:
        eat_zone = zoneinfo.ZoneInfo("Africa/Nairobi")
        current_time = datetime.now(eat_zone)
    except Exception:
        current_time = datetime.now()
        
    hour = current_time.hour
    if 5 <= hour < 12:
        greeting = "Good Morning"
    elif 12 <= hour < 17:
        greeting = "Good Afternoon"
    elif 17 <= hour < 22:
        greeting = "Good Evening"
    else:
        greeting = "Late Night Research Session"

    st.markdown(
        """
        <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
        /* Clean, highly readable typography & standard dark theme background */
        .stApp {
            background-color: #0e1117;
            color: #fafafa;
        }

        /* Remove any intrusive background blur overlays */
        div.stMarkdownContainer, .element-container {
            backdrop-filter: none !important;
        }

        /* Refined Professional Buttons */
        .stButton > button {
            background-color: #2563eb;
            color: #ffffff;
            border: 1px solid #3b82f6;
            font-weight: 500;
            border-radius: 6px;
            padding: 0.5rem 1rem;
        }
        .stButton > button:hover {
            background-color: #1d4ed8;
            border-color: #2563eb;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; background-color: #161b22; border: 1px solid #30363d; border-left: 4px solid #58a6ff; border-radius: 6px; margin-bottom: 15px;">
            <div>
                <span style="font-weight: 600; font-size: 1rem; color: #58a6ff;">{greeting}, Kula Chris</span>
                <span style="font-size: 0.85rem; color: #8b949e; margin-left: 10px;">ðŸ” Autonomous Research Intelligence Suite</span>
            </div>
            <div style="font-family: monospace; font-size: 0.85rem; color: #8b949e;">
                {current_time.strftime('%Y-%m-%d %H:%M:%S')} EAT
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

