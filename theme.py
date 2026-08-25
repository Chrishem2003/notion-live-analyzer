"""
CHRISHEM Unified Theme Engine - Single source of truth for all UI styling.
Eliminates 66+ duplicate CSS blocks across pages.

Design direction: "Precision Instrument Console" - a scientific analytical
instrument aesthetic (oscilloscope / spectrometer readout) rather than a
generic dark-dashboard look, matching the platform's actual subject matter
(statistics, nonlinear dynamics, genomics surveillance, GIS, ML).
"""

import streamlit as st

THEME = {
    "dark": {
        "bg_primary": "#0B0E11",
        "bg_secondary": "#12161C",
        "bg_card": "#171B23",
        "bg_sidebar": "#0D1014",
        "text_primary": "#EDEFF2",
        "text_secondary": "#A8B0BC",
        "text_muted": "#6B7280",
        "accent": "#E8A33D",
        "accent_alt": "#4FB8A6",
        "border": "#262B33",
        "border_accent": "#3A4048",
        "gradient_start": "#12161C",
        "gradient_end": "#2A1D0F",
        "success": "#34C787",
        "danger": "#E5484D",
        "warning": "#E8A33D",
    },
    "light": {
        "bg_primary": "#F4F6F8",
        "bg_secondary": "#E9EDF1",
        "bg_card": "#FFFFFF",
        "bg_sidebar": "#E3E8ED",
        "text_primary": "#171B23",
        "text_secondary": "#43505E",
        "text_muted": "#78838F",
        "accent": "#B5790E",
        "accent_alt": "#1F8E7A",
        "border": "#D7DEE5",
        "border_accent": "#C1CAD3",
        "gradient_start": "#FFFFFF",
        "gradient_end": "#F2E4C8",
        "success": "#1F8E5C",
        "danger": "#C4373C",
        "warning": "#B5790E",
    },
}


def get_theme():
    mode = st.session_state.get("theme_mode", "dark")
    return THEME.get(mode, THEME["dark"])


def render_theme_toggle():
    """Real dark/light switch. Renders a toggle that flips
    st.session_state['theme_mode'] and reruns so every themed element
    picks up the new palette immediately. Call once per page, ideally in
    the sidebar via page_bootstrap.setup_page()."""
    current = st.session_state.get("theme_mode", "dark")
    is_light = st.toggle(
        "\u2600\ufe0f Light mode",
        value=(current == "light"),
        key="theme_mode_toggle",
        help="Switch between dark and light interface themes.",
    )
    new_mode = "light" if is_light else "dark"
    if new_mode != current:
        st.session_state["theme_mode"] = new_mode
        st.rerun()


def inject_global_css():
    t = get_theme()

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            color: {t['text_primary']} !important;
        }}

        .stApp {{
            background: {t['bg_primary']};
            background-attachment: fixed;
        }}

        /* -- Sidebar -- */
        [data-testid="stSidebar"], section[data-testid="stSidebar"] {{
            background-color: {t['bg_sidebar']} !important;
            border-right: 1px solid {t['border']} !important;
        }}

        [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {{
            color: {t['text_primary']} !important;
        }}

        [data-testid="stSidebarNav"] span,
        [data-testid="stSidebarNav"] a,
        [data-testid="stSidebarHeader"] span,
        [data-testid="stSidebarHeader"] {{
            color: {t['text_primary']} !important;
            font-weight: 600 !important;
        }}

        [data-testid="stSidebarNavLink"]:hover,
        [data-testid="stSidebarNav"] a:hover {{
            background-color: {t['bg_card']} !important;
            border-radius: 6px !important;
        }}

        [data-testid="stSidebarNavLink"][aria-current="page"],
        [data-testid="stSidebarNav"] a[aria-selected="true"] {{
            background-color: {t['bg_card']} !important;
            color: {t['accent']} !important;
            font-weight: 700 !important;
            border-left: 3px solid {t['accent']} !important;
            border-radius: 4px !important;
        }}

        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stRadio label,
        section[data-testid="stSidebar"] .stMultiSelect label {{
            color: {t['accent_alt']} !important;
            font-weight: 700 !important;
        }}

        /* -- Typography -- */
        h1, h2, h3, h4, h5, h6 {{
            color: {t['text_primary']} !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em !important;
        }}

        h1::after, h2::after {{
            content: "";
            display: block;
            width: 2.5rem;
            height: 3px;
            background: {t['accent']};
            margin-top: 0.4rem;
            border-radius: 2px;
        }}

        p, span, label, div, .stMarkdown, .stCaption, .stRadio label, .stCheckbox label, .stSelectbox label {{
            color: {t['text_primary']};
        }}

        .stCaption {{
            color: {t['text_muted']} !important;
            font-size: 0.85rem !important;
        }}

        code, .stCode, .console-box {{
            font-family: 'IBM Plex Mono', monospace !important;
        }}

        /* -- Cards (signature: corner-bracket instrument-panel framing) -- */
        .chris-card, .chris-card-accent, .chris-card-success {{
            position: relative;
            background: {t['bg_card']};
            border: 1px solid {t['border']};
            border-radius: 6px;
            padding: 1.25rem;
            margin-bottom: 1.2rem;
        }}

        .chris-card::before, .chris-card-accent::before, .chris-card-success::before,
        .chris-card::after, .chris-card-accent::after, .chris-card-success::after {{
            content: "";
            position: absolute;
            width: 14px;
            height: 14px;
            border-color: {t['accent']};
            border-style: solid;
            opacity: 0.8;
        }}
        .chris-card::before, .chris-card-accent::before, .chris-card-success::before {{
            top: -1px; left: -1px;
            border-width: 2px 0 0 2px;
            border-top-left-radius: 6px;
        }}
        .chris-card::after, .chris-card-accent::after, .chris-card-success::after {{
            bottom: -1px; right: -1px;
            border-width: 0 2px 2px 0;
            border-bottom-right-radius: 6px;
        }}

        .chris-card-accent {{
            border-color: {t['accent']}66;
        }}

        .chris-card-success {{
            border-color: {t['success']}66;
        }}
        .chris-card-success::before, .chris-card-success::after {{
            border-color: {t['success']};
        }}

        /* -- Metrics -- */
        div[data-testid="stMetricValue"] {{
            color: {t['accent']} !important;
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 1.7rem !important;
            font-weight: 600 !important;
        }}
        div[data-testid="stMetricLabel"] {{
            color: {t['text_secondary']} !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            font-size: 0.72rem;
            letter-spacing: 0.06em;
        }}

        /* -- Inputs -- */
        div.stSelectbox, div.stMultiSelect, div.stTextInput, div.stNumberInput, div.stSlider, div[data-testid="stRadio"] {{
            background-color: {t['bg_card']} !important;
            border-radius: 6px !important;
        }}

        .stTextInput input, .stSelectbox div, .stNumberInput input, .stTextArea textarea {{
            background-color: {t['bg_card']} !important;
            color: {t['text_primary']} !important;
            border: 1px solid {t['border_accent']} !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
        }}

        .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {{
            border-color: {t['accent']} !important;
            box-shadow: 0 0 0 1px {t['accent']}55 !important;
        }}

        /* -- Buttons -- */
        .stButton button {{
            background: {t['bg_card']} !important;
            border: 1px solid {t['accent']} !important;
            color: {t['accent']} !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            transition: all 0.15s ease-in-out;
        }}
        .stButton button:hover {{
            background: {t['accent']} !important;
            color: {t['bg_primary']} !important;
        }}
        .stButton button[kind="primary"] {{
            background: {t['accent']} !important;
            color: {t['bg_primary']} !important;
        }}
        .stButton button[kind="primary"]:hover {{
            filter: brightness(1.1);
        }}

        /* -- DataFrames / Tables -- */
        .stDataFrame, .stTable {{
            background-color: {t['bg_secondary']} !important;
            border: 1px solid {t['border']} !important;
            border-radius: 6px !important;
        }}

        /* -- Tabs -- */
        div.stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            background-color: {t['bg_secondary']};
            padding: 5px;
            border-radius: 8px;
            border: 1px solid {t['border']};
        }}
        div.stTabs [data-baseweb="tab"] {{
            height: 40px;
            background-color: transparent;
            color: {t['text_secondary']};
            font-weight: 600 !important;
            border: none;
            padding: 0 16px;
            border-radius: 5px;
        }}
        div.stTabs [aria-selected="true"] {{
            background: {t['bg_card']} !important;
            color: {t['accent']} !important;
        }}

        /* -- Badges (LED-dot indicator style) -- */
        .badge-primary, .badge-success {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-family: 'IBM Plex Mono', monospace;
            letter-spacing: 0.04em;
            font-weight: 600;
        }}
        .badge-primary {{
            background: {t['accent_alt']}22;
            color: {t['accent_alt']};
        }}
        .badge-success {{
            background: {t['success']}22;
            color: {t['success']};
        }}
        .badge-primary::before, .badge-success::before {{
            content: "";
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: currentColor;
            display: inline-block;
        }}

        /* -- Dividers -- */
        .chris-hr {{
            height: 1px;
            background: linear-gradient(90deg, transparent, {t['border']}, transparent);
            margin: 1.5rem 0;
        }}

        /* -- Console Log -- */
        .console-box {{
            background: {t['bg_primary']};
            border: 1px solid {t['border']};
            border-radius: 6px;
            padding: 1rem;
            font-size: 0.85rem;
            color: {t['accent_alt']};
            max-height: 180px;
            overflow-y: auto;
        }}

        /* -- Status indicators (LED-dot) -- */
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.8rem;
        }}
        .status-badge::before {{
            content: "";
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: currentColor;
            box-shadow: 0 0 6px currentColor;
        }}
        .status-stable {{ background: {t['success']}1a; color: {t['success']}; border: 1px solid {t['success']}55; }}
        .status-critical {{ background: {t['danger']}1a; color: {t['danger']}; border: 1px solid {t['danger']}55; }}
        .status-warning {{ background: {t['warning']}1a; color: {t['warning']}; border: 1px solid {t['warning']}55; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
