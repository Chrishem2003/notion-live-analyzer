import security_guard
import security_guard

"""UI Styles  Design System & CSS Ingestion Engine."""
import streamlit as st

def apply_custom_styles():
    """Inject responsive dark/light mode CSS."""
    # Detect theme
    try:
        is_dark = st.get_option("theme.base") == "dark"
    except Exception:
        is_dark = False
    
    bg_color = "#0f172a" if is_dark else "#ffffff"
    text_color = "#f1f5f9" if is_dark else "#1e293b"
    card_bg = "#1e293b" if is_dark else "#f8fafc"
    border_color = "#334155" if is_dark else "#e2e8f0"
    accent = "#3b82f6"
    
    css = f"""
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
    /* Base */
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    
    /* Cards */
    .metric-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 1rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }}
    .metric-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: {card_bg};
        border-right: 1px solid {border_color};
    }}
    
    /* Buttons */
    .stButton > button {{
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59,130,246,0.3);
    }}
    
    /* Inputs */
    .stTextInput input, .stSelectbox, .stTextarea textarea {{
        border-radius: 8px !important;
        border: 1px solid {border_color} !important;
    }}
    .stTextInput input:focus {{
        border-color: {accent} !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
    }}
    
    /* Tables */
    [data-testid="stDataFrame"] {{
        border-radius: 8px;
        border: 1px solid {border_color};
    }}
    
    /* Status indicators */
    .status-connected {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.75rem;
        background: rgba(34,197,94,0.15);
        color: #22c55e;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
    }}
    .status-disconnected {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.75rem;
        background: rgba(239,68,68,0.15);
        color: #ef4444;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px 8px 0 0 !important;
        font-weight: 600;
    }}
    
    /* Metrics */
    [data-testid="stMetric"] {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 1rem;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
