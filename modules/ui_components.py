"""
UI Components — reusable Streamlit UI elements for consistent design.
"""
from typing import Optional, Dict, Any, List, Callable
import streamlit as st
from pathlib import Path
from modules.config import find_background_image, image_to_data_url, ASSETS_DIR, APP_DIR

# ─── CSS Theme Loading ────────────────────────────────────────────────
def load_css(is_dark: bool = False, accent_color: str = "#1d4ed8"):
    """Load and inject custom CSS with theme support."""
    background_path = find_background_image()
    background_css = ""
    if background_path:
        bg_url = image_to_data_url(background_path)
        background_css = (
            "background: linear-gradient(180deg, rgba(248, 251, 255, 0.94), rgba(238, 244, 255, 0.94)), "
            f"url('{bg_url}') center/cover no-repeat;"
        )

    if is_dark:
        bg_overlay = """
        background:
            linear-gradient(180deg, rgba(15, 23, 42, 0.85), rgba(15, 23, 42, 0.75)),
            radial-gradient(circle at top right, rgba(29, 78, 216, 0.15), transparent 55%);
        """
        text_color = "#e2e8f0"
        card_bg = "rgba(30, 41, 59, 0.9)"
        sidebar_bg = "linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92))"
    else:
        bg_overlay = """
        background:
            linear-gradient(180deg, rgba(15, 23, 42, 0.55), rgba(15, 23, 42, 0.35)),
            radial-gradient(circle at top right, rgba(29, 78, 216, 0.28), transparent 55%),
            radial-gradient(circle at bottom left, rgba(255, 255, 255, 0.18), transparent 45%);
        """
        text_color = "#0f172a"
        card_bg = "rgba(255, 255, 255, 0.78)"
        sidebar_bg = "linear-gradient(180deg, rgba(248, 251, 255, 0.96), rgba(241, 245, 249, 0.92))"

    st.markdown(
        f"""
        <style>
        .stApp {{
            {background_css}
            background-attachment: fixed;
            min-height: 100vh;
            background-size: cover;
        }}
        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            {bg_overlay}
            pointer-events: none;
            z-index: 0;
        }}
        .stApp::after {{
            content: "";
            position: fixed;
            inset: 0;
            background: {"rgba(0,0,0,0.15)" if is_dark else "rgba(248, 251, 255, 0.20)"};
            pointer-events: none;
            z-index: 0;
        }}
        .block-container {{
            position: relative;
            z-index: 1;
            padding-top: 1.75rem !important;
            padding-bottom: 2rem !important;
            max-width: 1320px !important;
        }}
        [data-testid="stSidebar"] {{
            background: {sidebar_bg};
            backdrop-filter: blur(16px);
            border-right: 1px solid rgba(189, 210, 255, 0.85);
            box-shadow: -12px 0 40px rgba(15, 23, 42, 0.10);
        }}
        [data-testid="stMetricValue"] {{
            color: {text_color} !important;
            font-size: 1.65rem !important;
            font-weight: 800 !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: #475569 !important;
            font-weight: 700 !important;
        }}
        .stPlotlyChart > div {{
            border-radius: 18px;
            overflow: hidden;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
        }}
        .hero-card {{
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(29, 78, 216, 0.92));
            color: white;
            padding: 1.35rem 1.5rem;
            border-radius: 22px;
            border: 1px solid rgba(255, 255, 255, 0.16);
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.25);
            backdrop-filter: blur(10px);
            margin-bottom: 1rem;
        }}
        .hero-card h1 {{
            color: #ffffff !important;
            margin-bottom: 0.15rem !important;
            font-size: 2rem !important;
            font-weight: 800 !important;
        }}
        .hero-card p {{
            color: #dbeafe !important;
            margin: 0.1rem 0 0.2rem 0 !important;
            font-size: 0.98rem !important;
        }}
        .status-pill {{
            display: inline-block;
            background: rgba(255,255,255,0.18);
            border: 1px solid rgba(255,255,255,0.22);
            color: #f8fafc;
            padding: 0.35rem 0.8rem;
            border-radius: 999px;
            font-size: 0.85rem;
            margin-top: 0.55rem;
            font-weight: 700;
        }}
        div[data-testid="stMetric"] {{
            background: {card_bg};
            backdrop-filter: blur(8px);
            border: 1px solid rgba(219, 228, 244, 0.95);
            border-radius: 18px;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
            padding: 0.55rem 0.75rem;
        }}
        .sidebar-card {{
            background: {"rgba(30, 41, 59, 0.95)" if is_dark else "linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.9))"};
            border: 1px solid rgba(219, 229, 248, 0.95);
            border-radius: 18px;
            padding: 0.95rem;
            margin: 0.45rem 0 0.9rem 0;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
        }}
        .sidebar-card .stSubheader,
        .sidebar-card .stCaption {{
            color: {text_color} !important;
        }}
        .section-header {{
            margin-top: 0.25rem;
            margin-bottom: 0.35rem;
        }}
        .section-header h3 {{
            color: {text_color} !important;
            font-size: 1.45rem !important;
            font-weight: 800 !important;
        }}
        .live-badge {{
            display: inline-block;
            padding: 0.35rem 0.8rem;
            border-radius: 999px;
            background: linear-gradient(135deg, #dbeafe, #bfdbfe);
            color: #1d4ed8;
            font-weight: 800;
            font-size: 0.85rem;
            margin-top: 0.5rem;
        }}
        .sync-card {{
            background: {"rgba(30, 41, 59, 0.85)" if is_dark else "linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(239, 246, 255, 0.92))"};
            border: 1px solid rgba(219, 229, 248, 0.95);
            border-radius: 18px;
            padding: 1rem 1.05rem;
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.1);
            margin-bottom: 1rem;
            backdrop-filter: blur(10px);
        }}
        div[data-testid="stDataFrame"] {{
            background: {card_bg};
            border-radius: 18px;
            overflow: hidden;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
        }}
        .stSubheader {{
            color: {text_color} !important;
            font-weight: 800 !important;
        }}
        .app-watermark {{
            position: fixed;
            right: 1.2rem;
            bottom: 0.9rem;
            font-size: clamp(3rem, 8vw, 6rem);
            font-weight: 900;
            letter-spacing: 0.18em;
            color: {"rgba(255,255,255,0.05)" if is_dark else "rgba(15, 23, 42, 0.08)"};
            pointer-events: none;
            z-index: 0;
            user-select: none;
            text-transform: uppercase;
            text-shadow: 0 0 18px rgba(255, 255, 255, 0.35);
        }}
        .stat-result-card {{
            background: {card_bg};
            border-radius: 14px;
            padding: 1rem;
            border: 1px solid rgba(219, 228, 244, 0.95);
            margin: 0.5rem 0;
        }}
        .insight-card {{
            background: {"rgba(30, 41, 59, 0.8)" if is_dark else "rgba(239, 246, 255, 0.85)"};
            border-left: 4px solid {accent_color};
            border-radius: 10px;
            padding: 0.8rem 1rem;
            margin: 0.4rem 0;
        }}
        .recommendation-card {{
            background: {"rgba(30, 41, 59, 0.8)" if is_dark else "rgba(255, 255, 255, 0.85)"};
            border: 1px solid rgba(219, 228, 244, 0.6);
            border-radius: 12px;
            padding: 0.8rem;
            margin: 0.4rem 0;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .recommendation-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.1);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ─── Common UI Elements ───────────────────────────────────────────────

def hero_card(title: str, subtitle: str, badge_text: str = None):
    """Render a styled hero card at the top of the page."""
    badge_html = f'<div class="status-pill">{badge_text}</div>' if badge_text else ""
    st.markdown(
        f"""
        <div class="hero-card">
            <h1>{title}</h1>
            <p>{subtitle}</p>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def section_header(title: str):
    """Render a section header."""
    st.markdown(f"<div class='section-header'><h3>{title}</h3></div>", unsafe_allow_html=True)

def sync_status_card(database_id: str, source: str, last_sync: str):
    """Render the sync status card."""
    st.markdown(
        f"""
        <div class="sync-card">
            <div><strong>✅ Connected to Notion database</strong></div>
            <div class="live-badge">{database_id}</div>
            <div style="margin-top: 0.45rem; color: #334155;">Source: {source}</div>
            <div style="margin-top: 0.35rem; color: #475569;">Last sync: {last_sync}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def sidebar_card(title: str, content: str = None):
    """Render a card inside the sidebar."""
    with st.sidebar:
        st.markdown("<div class='sidebar-card'>", unsafe_allow_html=True)
        st.subheader(title)
        if content:
            st.caption(content)
        return True  # For context manager

def end_sidebar_card():
    """Close a sidebar card."""
    st.markdown("</div>", unsafe_allow_html=True)

def stat_result_card(title: str, content: Any):
    """Render a statistical result in a styled card."""
    st.markdown("<div class='stat-result-card'>", unsafe_allow_html=True)
    st.subheader(title)
    if isinstance(content, str):
        st.markdown(content)
    elif isinstance(content, dict):
        for k, v in content.items():
            st.markdown(f"**{k}**: {v}")
    else:
        st.write(content)
    st.markdown("</div>", unsafe_allow_html=True)

def insight_card(icon: str, text: str):
    """Render an insight in a styled card."""
    st.markdown(
        f'<div class="insight-card">{icon} {text}</div>',
        unsafe_allow_html=True,
    )

def recommendation_card(title: str, description: str, is_active: bool = False):
    """Render a recommendation card."""
    border = f"border-left: 4px solid #1d4ed8;" if is_active else ""
    st.markdown(
        f'<div class="recommendation-card" style="{border}">'
        f'<strong>{title}</strong><br><small>{description}</small>'
        f'</div>',
        unsafe_allow_html=True,
    )

def watermark(text: str = "CHRISHEM"):
    """Render the app watermark."""
    st.markdown(f'<div class="app-watermark">{text}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# NOTION EMBED UI COMPONENTS
# ═══════════════════════════════════════════════════════════════════════

def notion_embed_container():
    """Wrap content in a Notion-embed-aware container."""
    compact = st.session_state.get("compact_mode", False)
    embed_mode = st.session_state.get("notion_embed_mode", False)
    classes = "notion-embed-container"
    if compact:
        classes += " notion-compact"
    st.markdown(f'<div class="{classes}">', unsafe_allow_html=True)
    return True  # For context manager usage

def end_notion_embed_container():
    """Close the notion embed container."""
    st.markdown('</div>', unsafe_allow_html=True)

def sticky_action_bar():
    """Render a sticky action bar at the top for quick actions."""
    st.markdown('<div class="sticky-action-bar">', unsafe_allow_html=True)
    return True

def end_sticky_action_bar():
    """Close the sticky action bar."""
    st.markdown('</div>', unsafe_allow_html=True)

def compact_metric(label: str, value, delta=None, help_text: str = None):
    """Render a compact metric card suitable for narrow Notion embeds."""
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.caption(label)
    with col2:
        st.markdown(f"<div style='font-size:1.3rem;font-weight:700;'>{value}</div>", unsafe_allow_html=True)
    with col3:
        if delta:
            st.markdown(f"<div style='font-size:0.9rem;color:#64748b;'>{delta}</div>", unsafe_allow_html=True)
    if help_text:
        st.caption(help_text)


def git_status_badge(connected: bool):
    """Render a Git connection status badge."""
    if connected:
        return '<span class="git-status-connected">● CONNECTED</span>'
    return '<span class="git-status-disconnected">○ DISCONNECTED</span>'


def execution_card(title: str, content: str, severity: str = "low"):
    """Render an executive report-style card with severity coloring."""
    colors = {"high": "#e74c3c", "medium": "#e67e22", "low": "#2ecc71"}
    color = colors.get(severity, "#64748b")
    st.markdown(f"""
    <div class="executive-card" style="border-left: 4px solid {color};">
        <h4 style="margin:0 0 0.3rem 0;color:{color};">{title}</h4>
        <p style="margin:0;color:#334155;font-size:0.95rem;">{content}</p>
    </div>
    """, unsafe_allow_html=True)


def render_onboarding_tour():
    """First-time user onboarding tour."""
    if st.session_state.get("show_onboarding", True):
        with st.expander("🎓 Welcome! Take a Quick Tour", expanded=True):
            st.markdown("""
            ### 👋 Welcome to the Advanced Research Data Analyzer!

            This powerful tool replaces **SPSS, Tableau, and Power BI** — all in one free, Notion-connected platform.

            **📍 Quick Navigation:**
            - **📊 Live Dashboard** — Real-time sync with your Notion database
            - **📁 File Analyzer** — Upload CSV, Excel, SPSS, SAS, STATA files
            - **🔬 Statistical Tests** — T-tests, ANOVA, Correlation, Regression, and more
            - **📈 Advanced Visuals** — 18+ chart types with auto-recommendation
            - **🤖 CHRISHEM Insights** — Automated data analysis and smart recommendations
            - **🔗 Git Integration** — Connect GitHub for data version control
            - **📊 Presentation Deck** — Build interactive slide decks
            - **⚙️ Settings** — Theme, credentials, keep-alive configuration

            **💡 Tips:**
            - Connect your Notion workspace OR upload a file to get started
            - CHRISHEM will automatically recommend the best analysis for your data
            - Enable Keep-Alive in Settings for 24/7 operation
            - Push cleaned data + analysis scripts back to GitHub
            """)
            if st.button("✅ Got it! Hide this tour"):
                st.session_state["show_onboarding"] = False
                st.rerun()

