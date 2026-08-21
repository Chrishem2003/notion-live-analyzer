"""
CHRISHEM Unified Theme Engine â€” Single source of truth for all UI styling.
Eliminates 66+ duplicate CSS blocks across pages.
"""

import streamlit as st

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# COLOR PALETTE CONSTANTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
THEME = {
    "dark": {
        "bg_primary": "#04080f",
        "bg_secondary": "#0b1321",
        "bg_card": "#111c2e",
        "bg_sidebar": "#090d16",
        "border": "#1e293b",
        "border_accent": "#00f2fe44",
        "text_primary": "#f8fafc",
        "text_secondary": "#cbd5e1",
        "text_muted": "#94a3b8",
        "accent": "#00f2fe",
        "accent_alt": "#38bdf8",
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#ef4444",
        "gradient_start": "#0b1e36",
        "gradient_end": "#061527",
    },
    "light": {
        "bg_primary": "#ffffff",
        "bg_secondary": "#f8fafc",
        "bg_card": "#ffffff",
        "bg_sidebar": "#f1f5f9",
        "border": "#e2e8f0",
        "border_accent": "#00f2fe88",
        "text_primary": "#0f172a",
        "text_secondary": "#334155",
        "text_muted": "#64748b",
        "accent": "#0284c7",
        "accent_alt": "#0ea5e9",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#dc2626",
        "gradient_start": "#e0f2fe",
        "gradient_end": "#f0f9ff",
    },
}


def get_theme():
    """Return active theme colors based on session state."""
    mode = st.session_state.get("theme_mode", "dark")
    return THEME.get(mode, THEME["dark"])


def inject_global_css():
    """
    Inject the unified CSS stylesheet ONCE into the app.
    Call this in app.py or the first page that loads.
    """
    t = get_theme()

    css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            color: {t['text_primary']} !important;
        }

        .stApp {{
            background: {t['bg_primary']};
            background-attachment: fixed;
        }

        /* â”€â”€ Sidebar â”€â”€ */
        [data-testid="stSidebar"], section[data-testid="stSidebar"] {{
            background-color: {t['bg_sidebar']} !important;
            border-right: 1px solid {t['border']} !important;
        }

        [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {{
            color: {t['text_primary']} !important;
        }

        [data-testid="stSidebarNav"] span, 
        [data-testid="stSidebarNav"] a,
        [data-testid="stSidebarNavLink"],
        [data-testid="stSidebarHeader"] {{
            color: {t['text_primary']} !important;
            font-weight: 600 !important;
        }

        [data-testid="stSidebarNavLink"]:hover,
        [data-testid="stSidebarNav"] a:hover {{
            background-color: {t['bg_card']} !important;
            border-radius: 8px !important;
        }

        [data-testid="stSidebarNavLink"][aria-current="page"],
        [data-testid="stSidebarNav"] a[aria-selected="true"] {{
            background-color: {t['accent']}33 !important;
            color: {t['accent']} !important;
            font-weight: 700 !important;
            border-radius: 8px !important;
        }

        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stRadio label,
        section[data-testid="stSidebar"] .stMultiSelect label {{
            color: {t['accent_alt']} !important;
            font-weight: 700 !important;
        }

        /* â”€â”€ Typography â”€â”€ */
        h1, h2, h3, h4, h5, h6 {{
            color: {t['accent']} !important;
            font-weight: 800 !important;
            letter-spacing: -0.025em !important;
        }

        p, span, label, div, .stMarkdown, .stCaption, .stRadio label, .stCheckbox label, .stSelectbox label {{
            color: {t['text_primary']} !important;
        }

        .stCaption {{
            color: {t['text_muted']} !important;
            font-size: 0.85rem !important;
        }

        /* â”€â”€ Cards â”€â”€ */
        .chris-card {{
            background: {t['bg_card']} !important;
            border: 1px solid {t['border_accent']} !important;
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1.2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }

        .chris-card-accent {{
            background: {t['bg_card']} !important;
            border: 1px solid {t['accent']} !important;
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1.2rem;
            box-shadow: 0 0 20px rgba(0, 242, 254, 0.1);
        }

        .chris-card-success {{
            background: #062419 !important;
            border: 1px solid {t['success']} !important;
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1.2rem;
        }

        /* â”€â”€ Metrics â”€â”€ */
        div[data-testid="stMetricValue"] {{
            color: {t['accent']} !important;
            font-size: 1.8rem !important;
            font-weight: 900 !important;
        }
        div[data-testid="stMetricLabel"] {{
            color: {t['text_secondary']} !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            font-size: 0.75rem;
        }

        /* â”€â”€ Inputs â”€â”€ */
        div.stSelectbox, div.stMultiSelect, div.stTextInput, div.stNumberInput, div.stSlider, div[data-testid="stRadio"] {{
            background-color: {t['bg_card']} !important;
            border-radius: 8px !important;
        }

        .stTextInput input, .stSelectbox div, .stNumberInput input, .stTextArea textarea {{
            background-color: {t['bg_card']} !important;
            color: {t['text_primary']} !important;
            border: 1px solid {t['accent']}88 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }

        /* â”€â”€ Buttons â”€â”€ */
        .stButton button {{
            background: {t['bg_card']} !important;
            border: 1px solid {t['accent']} !important;
            color: {t['accent']} !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
            transition: all 0.2s ease-in-out;
        }
        .stButton button:hover {{
            background: {t['accent']} !important;
            color: {t['bg_primary']} !important;
            box-shadow: 0 0 16px rgba(0, 242, 254, 0.5);
        }

        /* â”€â”€ DataFrames / Tables â”€â”€ */
        .stDataFrame, .stTable {{
            background-color: {t['bg_secondary']} !important;
            border: 1px solid {t['border']} !important;
            border-radius: 8px !important;
        }

        /* â”€â”€ Tabs â”€â”€ */
        div.stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: {t['bg_primary']};
            padding: 6px;
            border-radius: 10px;
            border: 1px solid {t['border']};
        }
        div.stTabs [data-baseweb="tab"] {{
            height: 42px;
            background-color: transparent;
            border-radius: 6px;
            color: {t['text_muted']} !important;
            font-weight: 700 !important;
            border: none;
            padding: 0 18px;
        }
        div.stTabs [aria-selected="true"] {{
            background: {t['bg_card']} !important;
            color: {t['accent']} !important;
            border-bottom: 3px solid {t['accent']} !important;
        }

        /* â”€â”€ Badges â”€â”€ */
        .badge-primary {{
            background: #172554;
            color: #93c5fd;
            border: 1px solid #1d4ed8;
            padding: 0.25rem 0.65rem;
            border-radius: 6px;
            font-size: 0.7rem;
            font-family: monospace;
            letter-spacing: 0.05em;
            font-weight: 700;
        }
        .badge-success {{
            background: #064e3b;
            color: #34d399;
            border: 1px solid #10b981;
            padding: 0.25rem 0.65rem;
            border-radius: 6px;
            font-size: 0.7rem;
            font-family: monospace;
            font-weight: 700;
        }

        /* â”€â”€ Dividers â”€â”€ */
        .chris-hr {{
            height: 1px;
            background: linear-gradient(90deg, transparent, {t['border']}, transparent);
            margin: 1.5rem 0;
        }

        /* â”€â”€ Console Log â”€â”€ */
        .console-box {{
            background: #030712;
            border: 1px solid {t['border']};
            border-radius: 8px;
            padding: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: {t['accent_alt']};
            max-height: 180px;
            overflow-y: auto;
        }

        /* â”€â”€ Progress / Status â”€â”€ */
        .status-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-weight: 700;
            font-size: 0.8rem;
        }
        .status-stable {{ background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid #059669; }
        .status-critical {{ background: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid #DC2626; }
        .status-warning {{ background: rgba(245, 158, 11, 0.2); color: #FBBF24; border: 1px solid #D97706; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

