"""Stunning UI Design System — Modern & Vibrant."""
import streamlit as st

def apply_stunning_styles():
    """Apply stunning modern CSS with vibrant colors and animations."""
    try:
        is_dark = st.get_option("theme.base") == "dark"
    except Exception:
        is_dark = True
    
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
    
    css = f"""
    <style>
    /* ═══════════════════════════════════════════════════════════════════
       STUNNING MODERN DESIGN SYSTEM
    ═══════════════════════════════════════════════════════════════════ */
    
    /* ─── Base ───────────────────────────────────────────────────────── */
    .stApp {{
        background: {bg};
        color: {text};
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
    
    /* ─── Typography ───────────────────────────────────────────────── */
    h1, h2, h3 {{
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }}
    h1 {{ font-size: 2.5rem !important; background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']}); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
    h2 {{ font-size: 1.75rem !important; color: {text} !important; }}
    h3 {{ font-size: 1.25rem !important; }}
    
    /* ─── Hero Banner ───────────────────────────────────────────────── */
    .hero-banner {{
        background: {hero_gradient};
        border-radius: 20px;
        padding: 2.5rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 20px 60px rgba(99, 102, 241, 0.3);
    }}
    .hero-banner::before {{
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
    .hero-banner h1 {{
        color: white !important;
        -webkit-text-fill-color: white !important;
        background: none !important;
        position: relative;
        z-index: 1;
    }}
    .hero-banner p {{
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        position: relative;
        z-index: 1;
    }}
    
    /* ─── Glass Cards ───────────────────────────────────────────────── */
    .glass-card {{
        background: {card_bg};
        border: 1px solid {border};
        border-radius: 16px;
        padding: 1.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
    }}
    .glass-card:hover {{
        border-color: {border_bright};
        transform: translateY(-4px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.2);
    }}
    
    /* Gradient border card */
    .gradient-card {{
        position: relative;
        background: {card_bg};
        border-radius: 16px;
        padding: 1.5rem;
    }}
    .gradient-card::before {{
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 16px;
        padding: 2px;
        background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']}, {colors['purple']});
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        pointer-events: none;
    }}
    
    /* ─── Stats Cards ───────────────────────────────────────────────── */
    .stat-card {{
        background: {card_gradient};
        border: 1px solid {border};
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }}
    .stat-card:hover {{
        transform: scale(1.02);
        box-shadow: 0 10px 30px rgba(99, 102, 241, 0.2);
    }}
    .stat-value {{
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1;
    }}
    .stat-label {{
        color: {text_muted};
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.5rem;
    }}
    
    /* ─── Sidebar ───────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: {card_bg};
        border-right: 1px solid {border};
        padding: 1rem;
    }}
    [data-testid="stSidebar"] .stRadio > div {{
        background: rgba(99, 102, 241, 0.1);
        border-radius: 12px;
        padding: 0.5rem;
    }}
    [data-testid="stSidebar"] .stRadio label {{
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{
        background: rgba(99, 102, 241, 0.2);
    }}
    [data-testid="stSidebar"] .stRadio label:has(input:checked) {{
        background: linear-gradient(135deg, {colors['primary']}, {colors['purple']}) !important;
        color: white !important;
    }}
    
    /* Sidebar title with gradient */
    [data-testid="stSidebar"] h1 {{
        background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']}) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        font-size: 1.5rem !important;
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
    .stButton > button:not([kind="primary"]) {{
        background: {card_bg};
        border: 1px solid {border} !important;
        color: {text};
    }}
    .stButton > button:not([kind="primary"]):hover {{
        border-color: {colors['primary']} !important;
        background: rgba(99, 102, 241, 0.1);
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
        font-weight: 700 !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {text_muted} !important;
    }}
    
    /* ─── DataFrame ─────────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {{
        border-radius: 16px;
        border: 1px solid {border};
        overflow: hidden;
    }}
    [data-testid="stDataFrame"] table {{
        background: {card_bg};
    }}
    [data-testid="stDataFrame"] thead th {{
        background: linear-gradient(135deg, {colors['primary']}, {colors['purple']}) !important;
        color: white !important;
        font-weight: 600;
        padding: 1rem !important;
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
    
    /* ─── Badges & Status ───────────────────────────────────────────── */
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
    .badge-premium {{
        background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']});
        color: white;
    }}
    
    /* Subscription tier */
    .tier-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.875rem;
    }}
    .tier-free {{
        background: rgba(107, 114, 128, 0.15);
        color: #9ca3af;
        border: 1px solid rgba(107, 114, 128, 0.3);
    }}
    .tier-standard {{
        background: rgba(99, 102, 241, 0.15);
        color: {colors['primary']};
        border: 1px solid {colors['primary']};
    }}
    .tier-premium {{
        background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']});
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
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
    
    /* ─── Spacing Helpers ───────────────────────────────────────────── */
    .spacer-h-1 {{ height: 0.5rem; }}
    .spacer-h-2 {{ height: 1rem; }}
    .spacer-h-3 {{ height: 1.5rem; }}
    .spacer-h-4 {{ height: 2rem; }}
    
    /* ─── Feature Cards Grid ────────────────────────────────────────── */
    .feature-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1.5rem;
    }}
    .feature-card {{
        background: {card_bg};
        border: 1px solid {border};
        border-radius: 16px;
        padding: 1.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    .feature-card:hover {{
        transform: translateY(-6px);
        border-color: {colors['primary']};
        box-shadow: 0 20px 40px rgba(0,0,0,0.15);
    }}
    .feature-icon {{
        width: 50px;
        height: 50px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        margin-bottom: 1rem;
        background: {hero_gradient};
    }}
    .feature-title {{
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
        color: {text};
    }}
    .feature-desc {{
        color: {text_muted};
        font-size: 0.9rem;
        line-height: 1.6;
    }}
    
    /* ─── Quick Action Buttons ─────────────────────────────────────── */
    .quick-action {{
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1.25rem;
        background: {card_bg};
        border: 1px solid {border};
        border-radius: 16px;
        cursor: pointer;
        transition: all 0.3s;
        text-align: left;
    }}
    .quick-action:hover {{
        border-color: {colors['primary']};
        transform: translateX(8px);
        background: rgba(99, 102, 241, 0.05);
    }}
    .quick-action-icon {{
        width: 45px;
        height: 45px;
        border-radius: 12px;
        background: {hero_gradient};
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
    }}
    .quick-action-title {{
        font-weight: 600;
        color: {text};
    }}
    .quick-action-desc {{
        font-size: 0.85rem;
        color: {text_muted};
    }}
    
    /* ─── Loading ──────────────────────────────────────────────────── */
    .loading-spinner {{
        width: 50px;
        height: 50px;
        border: 3px solid {border};
        border-top-color: {colors['primary']};
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }}
    @keyframes spin {{
        to {{ transform: rotate(360deg); }}
    }}
    
    /* ─── Toast / Alert Styling ────────────────────────────────────── */
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
    
    /* ─── Watermark ────────────────────────────────────────────────── */
    .watermark {{
        position: fixed;
        bottom: 15px;
        right: 20px;
        font-size: 12px;
        color: rgba(100, 100, 100, 0.25);
        font-weight: 700;
        letter-spacing: 3px;
        text-transform: uppercase;
        z-index: 1000;
    }}
    
    /* ─── Responsive ───────────────────────────────────────────────── */
    @media (max-width: 768px) {{
        .hero-banner {{ padding: 1.5rem; }}
        .hero-banner h1 {{ font-size: 1.75rem !important; }}
        .feature-grid {{ grid-template-columns: 1fr; }}
        .stat-value {{ font-size: 2rem; }}
    }}
    </style>
    
    <div class="watermark">CHRISHEM</div>
    """
    
    st.markdown(css, unsafe_allow_html=True)


def render_hero(title: str, subtitle: str = "", icon: str = ""):
    """Render a stunning hero section."""
    icon_html = f"{icon} " if icon else ""
    st.markdown(f"""
    <div class="hero-banner">
        <h1>{icon_html}{title}</h1>
        {f'<p>{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def render_stat(value: str, label: str, icon: str = ""):
    """Render a stat card."""
    icon_html = f"<div style='font-size: 1.5rem; margin-bottom: 0.5rem;'>{icon}</div>" if icon else ""
    st.markdown(f"""
    <div class="stat-card">
        {icon_html}
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_feature_card(icon: str, title: str, description: str):
    """Render a feature card."""
    st.markdown(f"""
    <div class="feature-card">
        <div class="feature-icon">{icon}</div>
        <div class="feature-title">{title}</div>
        <div class="feature-desc">{description}</div>
    </div>
    """, unsafe_allow_html=True)


def render_quick_action(icon: str, title: str, description: str, key: str = ""):
    """Render a quick action button."""
    st.markdown(f"""
    <div class="quick-action" onclick="document.getElementById('{key}')?.click()">
        <div class="quick-action-icon">{icon}</div>
        <div>
            <div class="quick-action-title">{title}</div>
            <div class="quick-action-desc">{description}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_badge(text: str, type: str = "primary"):
    """Render a status badge."""
    st.markdown(f'<span class="badge badge-{type}">{text}</span>', unsafe_allow_html=True)


def render_tier_badge(tier: str):
    """Render a subscription tier badge."""
    tier = tier.lower()
    icons = {"free": "🆓", "standard": "📘", "premium": "👑"}
    names = {"free": "Free", "standard": "Standard", "premium": "Premium"}
    icon = icons.get(tier, "🆓")
    name = names.get(tier, "Free")
    st.markdown(f'<span class="tier-badge tier-{tier}">{icon} {name}</span>', unsafe_allow_html=True)


def render_greeting():
    """Render contextual greeting with time & location."""
    from datetime import datetime
    
    hour = datetime.now().hour
    if hour < 12:
        time_greet = "☀️ Good morning"
    elif hour < 17:
        time_greet = "🌤️ Good afternoon"
    else:
        time_greet = "🌙 Good evening"
    
    # Special dates
    today = datetime.now().strftime("%m-%d")
    specials = {
        "01-01": "🎉 Happy New Year!",
        "07-04": "🇺🇸 Happy Independence Day!",
        "10-31": "🎃 Happy Halloween!",
        "12-25": "🎄 Merry Christmas!",
        "10-01": "🇳🇬 Happy Independence Day!",
    }
    
    special = specials.get(today, "")
    greeting = f"{time_greet} {special}".strip()
    
    return greeting