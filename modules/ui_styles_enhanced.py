"""Enhanced UI Styles — Visual Design System."""
import streamlit as st

def apply_enhanced_styles():
    """Apply enhanced custom CSS with breathing animations."""
    try:
        is_dark = st.get_option("theme.base") == "dark"
    except Exception:
        is_dark = False
    
    # Color palette
    bg_color = "#0f172a" if is_dark else "#ffffff"
    text_color = "#f1f5f9" if is_dark else "#1e293b"
    card_bg = "#1e293b" if is_dark else "#f8fafc"
    border_color = "#334155" if is_dark else "#e2e8f0"
    accent = "#3b82f6"
    accent_gradient = "linear-gradient(135deg, #3b82f6, #8b5cf6)"
    
    # Enhanced CSS
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
    /* ─── Base ───────────────────────────────────────────────────────── */
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    
    /* ─── Background Image with Watermark ───────────────────────────── */
    [data-testid="stAppViewContainer"] {{
        position: relative;
    }}
    [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-image: url("https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=1920");
        background-size: cover;
        background-position: center;
        opacity: 0.08;
        z-index: -1;
    }}
    
    /* CHRISHEM Watermark */
    .app-watermark {{
        position: fixed;
        bottom: 20px;
        right: 20px;
        font-size: 14px;
        color: rgba(100, 100, 100, 0.3);
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        z-index: 1000;
    }}
    
    /* ─── Cards ─────────────────────────────────────────────────────── */
    .metric-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 1rem;
        transition: all 0.3s ease;
    }}
    .metric-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(0,0,0,0.2);
        border-color: {accent};
    }}
    
    /* ─── Breathing Gradient Animation ─────────────────────────────── */
    @keyframes breathe-gradient {{
        0%, 100% {{
            background: linear-gradient(135deg, rgba(59,130,246,0.1), rgba(139,92,246,0.1));
        }}
        50% {{
            background: linear-gradient(135deg, rgba(139,92,246,0.15), rgba(59,130,246,0.15));
        }}
    }}
    
    .breathing-card {{
        animation: breathe-gradient 4s ease-in-out infinite;
        border-radius: 12px;
        padding: 1rem;
    }}
    
    /* Sidebar breathing effect */
    [data-testid="stSidebar"] {{
        animation: breathe-gradient 6s ease-in-out infinite;
    }}
    
    /* Primary action button animation */
    .stButton > button[kind="primary"] {{
        background: {accent_gradient};
        border: none;
        transition: all 0.3s ease;
    }}
    .stButton > button[kind="primary"]:hover {{
        transform: scale(1.02);
        box-shadow: 0 8px 24px rgba(59,130,246,0.4);
    }}
    
    /* ─── Sidebar ─────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: {card_bg};
        border-right: 1px solid {border_color};
    }}
    
    /* ─── Status Indicators ────────────────────────────────────────── */
    .status-connected, .status-active {{
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
    .status-disconnected, .status-inactive {{
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
    .status-trial {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.75rem;
        background: rgba(245,158,11,0.15);
        color: #f59e0b;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
    }}
    .status-verified {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.75rem;
        background: rgba(59,130,246,0.15);
        color: #3b82f6;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
    }}
    
    /* ─── Tier Badges ──────────────────────────────────────────────── */
    .tier-badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
    }}
    .tier-free {{
        background: rgba(107,114,128,0.2);
        color: #9ca3af;
    }}
    .tier-standard {{
        background: rgba(59,130,246,0.2);
        color: #3b82f6;
    }}
    .tier-premium {{
        background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(59,130,246,0.2));
        color: #8b5cf6;
    }}
    
    /* ─── Tab Styling ───────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px 8px 0 0 !important;
        font-weight: 600;
        transition: all 0.2s;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        background: rgba(59,130,246,0.1);
    }}
    
    /* ─── DataFrames & Tables ───────────────────────────────────────── */
    [data-testid="stDataFrame"] {{
        border-radius: 12px;
        border: 1px solid {border_color};
    }}
    
    /* ─── Input Focus ───────────────────────────────────────────────── */
    .stTextInput input:focus, .stTextarea textarea:focus {{
        border-color: {accent} !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
    }}
    
    /* ─── Expanders ─────────────────────────────────────────────────── */
    .streamlit-expanderHeader {{
        background: {card_bg};
        border-radius: 12px !important;
        font-weight: 600;
    }}
    
    /* ─── Hero Section ──────────────────────────────────────────────── */
    .hero-card {{
        background: {accent_gradient};
        color: white;
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
    }}
    .hero-card h1 {{
        margin: 0;
        font-size: 2rem;
    }}
    .hero-card p {{
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }}
    
    /* ─── Feature Cards ─────────────────────────────────────────────── */
    .feature-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
    }}
    .feature-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 1.25rem;
        transition: all 0.3s ease;
    }}
    .feature-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        border-color: {accent};
    }}
    .feature-icon {{
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }}
    .feature-title {{
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 0.25rem;
    }}
    .feature-desc {{
        font-size: 0.85rem;
        color: {'#94a3b8' if is_dark else '#64748b'};
    }}
    
    /* ─── Notification Badge ────────────────────────────────────────── */
    .notification-badge {{
        position: absolute;
        top: -5px;
        right: -5px;
        background: #ef4444;
        color: white;
        border-radius: 50%;
        width: 18px;
        height: 18px;
        font-size: 0.65rem;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    
    /* ─── Loading Spinner ───────────────────────────────────────────── */
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.5; }}
    }}
    .loading-pulse {{
        animation: pulse 1.5s ease-in-out infinite;
    }}
    
    /* ─── Tooltips ──────────────────────────────────────────────────── */
    .tooltip {{
        position: relative;
        display: inline-block;
    }}
    .tooltip .tooltiptext {{
        visibility: hidden;
        background: {text_color};
        color: {bg_color};
        padding: 5px 10px;
        border-radius: 6px;
        font-size: 12px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        transform: translateX(-50%);
        white-space: nowrap;
    }}
    .tooltip:hover .tooltiptext {{
        visibility: visible;
    }}
    
    /* ─── Responsive ────────────────────────────────────────────────── */
    @media (max-width: 768px) {{
        .block-container {{
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }}
        .hero-card h1 {{
            font-size: 1.5rem;
        }}
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
    
    <!-- Watermark -->
    <div class="app-watermark">CHRISHEM</div>
    """
    
    st.markdown(css, unsafe_allow_html=True)

def render_tier_badge(tier: str):
    """Render a tier badge."""
    tier_classes = {
        "free": "tier-free",
        "standard": "tier-standard", 
        "premium": "tier-premium",
    }
    tier_names = {
        "free": "🆓 Free",
        "standard": "📘 Standard",
        "premium": "👑 Premium",
    }
    
    cls = tier_classes.get(tier.lower(), "tier-free")
    name = tier_names.get(tier.lower(), "Free")
    
    st.markdown(f'<span class="tier-badge {cls}">{name}</span>', unsafe_allow_html=True)

def render_status_indicator(status: str):
    """Render a status indicator."""
    status_classes = {
        "active": "status-active",
        "connected": "status-connected",
        "inactive": "status-inactive",
        "disconnected": "status-disconnected",
        "trial": "status-trial",
        "verified": "status-verified",
    }
    
    cls = status_classes.get(status.lower(), "status-inactive")
    display = status.replace("_", " ").title()
    
    st.markdown(f'<span class="{cls}">● {display}</span>', unsafe_allow_html=True)

def render_feature_card(icon: str, title: str, description: str):
    """Render a feature card."""
    st.markdown(f"""
    <div class="feature-card">
        <div class="feature-icon">{icon}</div>
        <div class="feature-title">{title}</div>
        <div class="feature-desc">{description}</div>
    </div>
    """, unsafe_allow_html=True)

def render_hero_section(title: str, subtitle: str = ""):
    """Render a hero section header."""
    st.markdown(f"""
    <div class="hero-card">
        <h1>{title}</h1>
        {f'<p>{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)

def render_location_greeting():
    """Render contextual greeting based on user location/holidays."""
    from datetime import datetime
    import random
    
    now = datetime.now()
    hour = now.hour
    
    # Time-based greeting
    if hour < 12:
        greeting = "☀️ Good morning"
    elif hour < 17:
        greeting = "🌤️ Good afternoon"
    else:
        greeting = "🌙 Good evening"
    
    # Check for special dates
    special_days = {
        "01-01": "🎉 Happy New Year!",
        "07-04": "🇺🇸 Happy Independence Day!",
        "10-31": "🎃 Happy Halloween!",
        "12-25": "🎄 Merry Christmas!",
        "01-01": "🎊 Happy New Year!",
        "03-08": "🌸 Happy International Women's Day!",
        "06-12": "🇳🇬 Happy June 12!",
        "10-01": "🇳🇬 Happy Independence Day!",
    }
    
    date_key = now.strftime("%m-%d")
    special = special_days.get(date_key, "")
    
    if special:
        greeting = f"{greeting} {special}"
    
    return greeting
