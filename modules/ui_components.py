"""
UI Components — reusable Streamlit UI elements for consistent design.
Unified stunning styling system for all pages.
"""
from typing import Optional, Dict, Any, List, Callable
import streamlit as st
from pathlib import Path
from modules.config import find_background_image, image_to_data_url, ASSETS_DIR, APP_DIR

# ─── Unified Stunning Styles (Applied everywhere) ─────────────────────
def load_css(is_dark: bool = False, accent_color: str = "#6366f1"):
    """Load unified stunning CSS with vibrant colors and animations."""
    # Try to detect theme
    try:
        is_dark = st.get_option("theme.base") == "dark"
    except Exception:
        pass
    
    # Stunning vibrant color palette
    colors = {
        "primary": "#6366f1",        # Indigo
        "primary_dark": "#4f46e5",
        "secondary": "#ec4899",      # Pink
        "accent": "#14b8a6",         # Teal
        "success": "#22c55e",        # Green
        "warning": "#f59e0b",        # Amber
        "error": "#ef4444",          # Red
        "purple": "#8b5cf6",
        "cyan": "#06b6d4",
        "orange": "#f97316",
    }
    
    # Gradients
    hero_gradient = f"linear-gradient(135deg, {colors['primary']} 0%, {colors['purple']} 50%, {colors['secondary']} 100%)"
    card_gradient = f"linear-gradient(145deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)"
    mesh_gradient = f"radial-gradient(at 40% 20%, {colors['primary']}20 0px, transparent 50%), radial-gradient(at 80% 0%, {colors['secondary']}20 0px, transparent 50%), radial-gradient(at 0% 50%, {colors['accent']}20 0px, transparent 50%), radial-gradient(at 80% 50%, {colors['purple']}20 0px, transparent 50%), radial-gradient(at 0% 100%, {colors['cyan']}20 0px, transparent 50%)"
    
    bg = "#0a0a0f" if is_dark else "#fafbfc"
    card_bg = "#12121a" if is_dark else "#ffffff"
    text = "#f8fafc" if is_dark else "#1e293b"
    text_muted = "#94a3b8" if is_dark else "#64748b"
    border = "rgba(99, 102, 241, 0.15)"
    border_bright = "rgba(99, 102, 241, 0.3)"
    
    # Get background image
    background_path = find_background_image()
    background_css = ""
    if background_path:
        bg_url = image_to_data_url(background_path)
        background_css = (
            "background: linear-gradient(180deg, rgba(248, 251, 255, 0.94), rgba(238, 244, 255, 0.94)), "
            f"url('{bg_url}') center/cover no-repeat;"
        )
    
    # Build overlay for dark/light mode
    if is_dark:
        bg_overlay = """
        background:
            linear-gradient(180deg, rgba(15, 23, 42, 0.85), rgba(15, 23, 42, 0.75)),
            radial-gradient(circle at top right, rgba(29, 78, 216, 0.15), transparent 55%);
        """
        text_color = "#e2e8f0"
        side_card_bg = "rgba(30, 41, 59, 0.9)"
        sidebar_bg = "linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92))"
    else:
        bg_overlay = """
        background:
            linear-gradient(180deg, rgba(15, 23, 42, 0.55), rgba(15, 23, 42, 0.35)),
            radial-gradient(circle at top right, rgba(29, 78, 216, 0.28), transparent 55%),
            radial-gradient(circle at bottom left, rgba(255, 255, 255, 0.18), transparent 45%);
        """
        text_color = "#0f172a"
        side_card_bg = "rgba(255, 255, 255, 0.78)"
        sidebar_bg = "linear-gradient(180deg, rgba(248, 251, 255, 0.96), rgba(241, 245, 249, 0.92))"
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
        /* ═══════════════════════════════════════════════════════════════════
           UNIFIED STUNNING DESIGN SYSTEM — All Pages
        ═══════════════════════════════════════════════════════════════════ */
        
        /* ─── Base ───────────────────────────────────────────────────────── */
        .stApp {{
            {background_css}
            background-attachment: fixed;
            min-height: 100vh;
            background-size: cover;
        }}
        
        /* Animated mesh gradient background */
        [data-testid="stAppViewContainer"] {{
            position: relative;
            overflow: hidden;
        }}
        [data-testid="stAppViewContainer"]::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: {mesh_gradient};
            opacity: 0.6;
            z-index: -1;
            animation: mesh-move 20s ease-in-out infinite;
        }}
        @keyframes mesh-move {{
            0%, 100% {{ transform: scale(1) rotate(0deg); }}
            50% {{ transform: scale(1.1) rotate(2deg); }}
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
        
        /* ─── Typography ───────────────────────────────────────────────── */
        h1, h2, h3 {{
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }}
        h1 {{ font-size: 2.5rem !important; background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']}); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
        h2 {{ font-size: 1.75rem !important; color: {text} !important; }}
        h3 {{ font-size: 1.25rem !important; }}
        
        /* ─── Sidebar ───────────────────────────────────────────────────── */
        [data-testid="stSidebar"] {{
            background: {sidebar_bg};
            backdrop-filter: blur(16px);
            border-right: 1px solid rgba(189, 210, 255, 0.85);
            box-shadow: -12px 0 40px rgba(15, 23, 42, 0.10);
        }}
        [data-testid="stSidebar"] h1 {{
            background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']}) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            font-size: 1.5rem !important;
        }}
        
        /* ─── Hero Banner ───────────────────────────────────────────────── */
        .hero-card {{
            background: {hero_gradient};
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            position: relative;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(99, 102, 241, 0.3);
        }}
        .hero-card::before {{
            content: "";
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
            animation: hero-shimmer 3s ease-in-out infinite;
        }}
        @keyframes hero-shimmer {{
            0%, 100% {{ transform: translate(-10%, -10%); }}
            50% {{ transform: translate(10%, 10%); }}
        }}
        .hero-card h1 {{
            color: white !important;
            -webkit-text-fill-color: white !important;
            background: none !important;
            position: relative;
            z-index: 1;
            margin-bottom: 0.15rem !important;
            font-size: 2rem !important;
            font-weight: 800 !important;
        }}
        .hero-card p {{
            color: rgba(255,255,255,0.9);
            font-size: 1rem;
            position: relative;
            z-index: 1;
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
        
        /* ─── Metrics ───────────────────────────────────────────────────── */
        [data-testid="stMetric"] {{
            background: {card_bg};
            border: 1px solid {border};
            border-radius: 16px;
            padding: 1.25rem;
            transition: all 0.3s;
        }}
        [data-testid="stMetric"]:hover {{
            border-color: {border_bright};
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
        }}
        [data-testid="stMetricValue"] {{
            color: {colors['primary']} !important;
            font-size: 1.65rem !important;
            font-weight: 800 !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: {text_muted} !important;
            font-weight: 700 !important;
        }}
        
        /* ─── Charts ────────────────────────────────────────────────────�� */
        .stPlotlyChart > div {{
            border-radius: 18px;
            overflow: hidden;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
        }}
        
        /* ─── DataFrame ─────────────────────────────────────────────────── */
        [data-testid="stDataFrame"] {{
            background: {card_bg};
            border-radius: 16px;
            border: 1px solid {border};
            overflow: hidden;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
        }}
        [data-testid="stDataFrame"] thead th {{
            background: linear-gradient(135deg, {colors['primary']}, {colors['purple']}) !important;
            color: white !important;
            font-weight: 600;
            padding: 1rem !important;
        }}
        
        /* ─── Buttons ───────────────────────────────────────────────────── */
        .stButton > button {{
            border-radius: 12px !important;
            font-weight: 600 !important;
            padding: 0.75rem 1.5rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            border: none !important;
        }}
        .stButton > button[kind="primary"] {{
            background: {hero_gradient} !important;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4) !important;
        }}
        
        /* ─── Inputs ────────────────────────────────────────────────────── */
        .stTextInput input, .stTextArea textarea, .stSelectbox {{
            background: {card_bg} !important;
            border: 1px solid {border} !important;
            border-radius: 12px !important;
            padding: 0.75rem 1rem !important;
            transition: all 0.2s;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border-color: {colors['primary']} !important;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
        }}
        
        /* ─── Tabs ──────────────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.5rem;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 10px 10px 0 0 !important;
            padding: 0.75rem 1.5rem !important;
            font-weight: 600;
            background: transparent !important;
            transition: all 0.2s;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            background: rgba(99, 102, 241, 0.1) !important;
        }}
        .stTabs [aria-selected="true"] {{
            background: linear-gradient(135deg, {colors['primary']}, {colors['purple']}) !important;
            color: white !important;
        }}
        
        /* ─── Sidebar Card ───────────────────────────────────────────────── */
        .sidebar-card {{
            background: {side_card_bg};
            border: 1px solid {border};
            border-radius: 18px;
            padding: 0.95rem;
            margin: 0.45rem 0 0.9rem 0;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
        }}
        .sidebar-card .stSubheader,
        .sidebar-card .stCaption {{
            color: {text} !important;
        }}
        
        /* ─── Section Header ────────────────────────────────────────────── */
        .section-header {{
            margin-top: 0.25rem;
            margin-bottom: 0.35rem;
        }}
        .section-header h3 {{
            color: {text} !important;
            font-size: 1.45rem !important;
            font-weight: 800 !important;
        }}
        .stSubheader {{
            color: {text} !important;
            font-weight: 800 !important;
        }}
        
        /* ─── Live Badge ───────────────────────────────────────────────── */
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
        
        /* ─── Insight & Recommendation Cards ───────────────────────────── */
        .insight-card {{
            background: {card_gradient};
            border-left: 4px solid {colors['primary']};
            border-radius: 10px;
            padding: 0.8rem 1rem;
            margin: 0.4rem 0;
        }}
        .recommendation-card {{
            background: {card_bg};
            border: 1px solid {border};
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
        
        /* ─── Sync Card ────────────────────────────────────────────────── */
        .sync-card {{
            background: {card_bg};
            border: 1px solid {border};
            border-radius: 18px;
            padding: 1rem 1.05rem;
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.1);
            margin-bottom: 1rem;
            backdrop-filter: blur(10px);
        }}
        
        /* ─── Stat Result Card ─────────────────────────────────────────── */
        .stat-result-card {{
            background: {card_bg};
            border-radius: 14px;
            padding: 1rem;
            border: 1px solid {border};
            margin: 0.5rem 0;
        }}
        
        /* ─── Watermark ────────────────────────────────────────────────── */
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
        
        /* ─── Status Badges ────────────────────────────────────────────── */
        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.35rem 0.85rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}
        .badge-success {{
            background: rgba(34, 197, 94, 0.15);
            color: {colors['success']};
        }}
        .badge-warning {{
            background: rgba(245, 158, 11, 0.15);
            color: {colors['warning']};
        }}
        .badge-error {{
            background: rgba(239, 68, 68, 0.15);
            color: {colors['error']};
        }}
        .badge-primary {{
            background: rgba(99, 102, 241, 0.15);
            color: {colors['primary']};
        }}
        
        /* ─── Animations ────────────────────────────────────────────────── */
        @keyframes fade-in {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .animate-fade-in {{
            animation: fade-in 0.5s ease-out forwards;
        }}
        
        @keyframes pulse-glow {{
            0%, 100% {{ box-shadow: 0 0 20px rgba(99, 102, 241, 0.2); }}
            50% {{ box-shadow: 0 0 40px rgba(99, 102, 241, 0.4); }}
        }}
        .pulse-glow {{
            animation: pulse-glow 2s ease-in-out infinite;
        }}
        
        /* ─── Expanders ─────────────────────────────────────────────────── */
        .streamlit-expanderHeader {{
            background: {card_bg};
            border: 1px solid {border};
            border-radius: 12px !important;
            font-weight: 600;
            padding: 1rem !important;
            transition: all 0.2s;
        }}
        .streamlit-expanderHeader:hover {{
            border-color: {colors['primary']};
        }}
        
        /* ─── Alerts ────────────────────────────────────────────────────── */
        .stSuccess, .stInfo, .stWarning, .stError {{
            border-radius: 12px !important;
            border: none !important;
        }}
        .stSuccess {{ background: rgba(34, 197, 94, 0.15) !important; color: {colors['success']} !important; }}
        .stInfo {{ background: rgba(99, 102, 241, 0.15) !important; color: {colors['primary']} !important; }}
        .stWarning {{ background: rgba(245, 158, 11, 0.15) !important; color: {colors['warning']} !important; }}
        .stError {{ background: rgba(239, 68, 68, 0.15) !important; color: {colors['error']} !important; }}
        
        /* ─── Dividers ──────────────────────────────────────────────────── */
        hr {{
            border: none;
            height: 1px;
            background: linear-gradient(90deg, transparent, {border_bright}, transparent);
            margin: 2rem 0;
        }}
        
        /* ─── Responsive ───────────────────────────────────────────────── */
        @media (max-width: 768px) {{
            .hero-card {{ padding: 1.5rem; }}
            .hero-card h1 {{ font-size: 1.75rem !important; }}
            [data-testid="column"] {{
                min-width: 100% !important;
            }}
        }}
        
        /* ─── Print ─────────────────────────────────────────────────────── */
        @media print {{
            .app-watermark {{
                display: block !important;
                color: #999;
            }}
            [data-testid="stSidebar"] {{
                display: none !important;
            }}
        }}
        </style>
        
        <div class="app-watermark">CHRISHEM</div>
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


