import datetime
import io
import json
import sqlite3
import numpy as np
import pandas as pd
import streamlit as st
from scipy.integrate import odeint

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================
def init_db():
    conn = sqlite3.connect("sovereign_engine.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            author TEXT,
            org_email TEXT,
            jurisdiction TEXT,
            sector TEXT,
            role TEXT,
            mlce_heuristic REAL,
            state_label TEXT,
            recommendation TEXT,
            risk_score REAL,
            params TEXT,
            notes TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_presets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preset_name TEXT UNIQUE,
            sector TEXT,
            custom_dx TEXT,
            custom_dy TEXT,
            custom_dz TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyst_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analyst_name TEXT UNIQUE,
            org_email TEXT,
            contact_phone TEXT,
            clearance_level TEXT,
            primary_sector TEXT,
            vault_hash TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO analyst_contacts (analyst_name, org_email, contact_phone, clearance_level, primary_sector, vault_hash)
        VALUES 
        ('Kula Chris', 'chrishem@sovereign.org', '+256 700 000000', 'Tier-1 Lead Architect', 'Economics & Sovereign Risk', 'HASH-SOV-999'),
        ('Dr. Matsiko', 'matsiko@muni.ac.ug', '+256 772 111222', 'Chief Scientific Director', 'Bioinformatics & Systems', 'HASH-SCI-888'),
        ('Ocircan Darius', 'darius@sovereign.org', '+256 750 333444', 'Senior Policy Analyst', 'Infrastructure & Grid', 'HASH-POL-777')
    """)
    conn.commit()
    return conn

db_conn = init_db()

# ============================================================================
# PAGE CONFIG & STYLES
# ============================================================================
st.set_page_config(
    page_title="Sovereign Real-Time Decision & Risk Engine",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #F8FAFC !important; }
    .stApp { background: linear-gradient(135deg, #070B14 0%, #0F172A 50%, #070B14 100%); background-attachment: fixed; }
    .glass-container {
        background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 20px;
        padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6);
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 16px; padding: 1.2rem; text-align: center;
    }
    .metric-value { font-size: 1.8rem; font-weight: 800; background: linear-gradient(90deg, #60A5FA, #A78BFA); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .metric-label { font-size: 0.8rem; color: #CBD5E1 !important; text-transform: uppercase; font-weight: 600; margin-top: 0.2rem; }
    .status-indicator { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; border-radius: 9999px; font-weight: 700; font-size: 0.85rem; }
    .status-invest { background: rgba(22, 101, 52, 0.4); border: 1px solid #4ADE80; color: #4ADE80 !important; }
    .status-hold { background: rgba(133, 77, 14, 0.4); border: 1px solid #FACC15; color: #FACC15 !important; }
    .status-pullback { background: rgba(153, 27, 27, 0.4); border: 1px solid #F87171; color: #F87171 !important; }
    .main-header-glow { background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.2rem; font-weight: 800; }
    .glass-divider { height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent); margin: 1.2rem 0; }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADER
# ============================================================================
def _load_any(uploaded_file):
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"): return pd.read_csv(uploaded_file)
        if name.endswith(".json"): return pd.read_json(uploaded_file)
        if name.endswith((".xlsx", ".xls")): return pd.read_excel(uploaded_file)
        if name.endswith(".txt"): return pd.read_csv(uploaded_file, sep=None, engine="python")
        st.error("Unsupported file format.")
        return None
    except Exception as exc:
        st.error(f"Error reading {uploaded_file.name}: {exc}")
        return None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Real-Time Decision Intelligence Engine Active. Ask for sector guidance, shock assessments, or investment timing triggers."}
    ]

# ============================================================================
# SIDEBAR CONTROLS
# ============================================================================
st.sidebar.markdown("## ?? Sovereign Decision Core")

with st.sidebar.expander("?? Institutional & User Context", expanded=True):
    user_role = st.selectbox(
        "Module Tier",
        [
            "? Decision & Action Engine",
            "?? Chat Command Core",
            "?? Executive Storyboard",
            "?? Policy Strategy Matrix",
            "?? Sector Operational Risk",
            "?? Research & Nonlinear Analytics",
            "?? Real-Time Data Ingestion",
            "?? Directory & Analyst Contacts"
        ],
    )
    author_name = st.text_input("Analyst / Operator", "Kula Chris")
    org_email = st.text_input("Email", "chrishem@sovereign.org")

st.sidebar.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown("### ?? Location & Sector Setup")

PRESET_COUNTRIES = ["🔍 Uganda", "🔍 Kenya", "🔍 Rwanda", "🔍 Nigeria", "🔍 South Africa", "🔍 United States", "??B United Kingdom", "?? Global Aggregate"]
target_country = st.sidebar.selectbox("Country / Region", PRESET_COUNTRIES, index=0)
specific_location = st.sidebar.text_input("Sub-location / Facility (Optional)", "e.g., Kampala Central / Mulago Hospital")

PRESET_SECTORS = {
    "?? Economics & Markets": ("a", "Growth Drive", "b", "Capital Cost / Friction", "c", "Market Reserve Buffer"),
    "?? Healthcare & Hospitals": ("a", "Inflow Rate", "b", "ICU Burnout / Friction", "c", "Resource Reserve"),
    "?? Education & Institutions": ("a", "Enrollment Velocity", "b", "Overhead Cost", "c", "Liquidity Buffer"),
    "?? Agriculture & Food Security": ("a", "Yield Stress Drive", "b", "Supply Friction", "c", "Strategic Reserve"),
    "? Infrastructure & Energy": ("a", "Load Surge Rate", "b", "Grid Resistance", "c", "Capacity Buffer"),
}

sector_key = st.sidebar.selectbox("Sector Domain", list(PRESET_SECTORS.keys()))
a_lbl, a_desc, b_lbl, b_desc, c_lbl, c_desc = PRESET_SECTORS[sector_key]

st.sidebar.markdown(f"### ?? Dynamics � {sector_key}")
a = st.sidebar.slider(f"{a_lbl} ({a_desc})", 0.1, 5.0, 1.5, 0.1)
b = st.sidebar.slider(f"{b_lbl} ({b_desc})", 0.0, 3.0, 0.9, 0.1)
c = st.sidebar.slider(f"{c_lbl} ({c_desc})", 0.0, 3.0, 1.0, 0.1)

policy_shock = st.sidebar.slider("Inject Stress / Shock Magnitude", -3.0, 3.0, 0.0, 0.1)
t_max = st.sidebar.slider("Forecast Horizon (Steps)", 50, 500, 200, 10)

# ============================================================================
# SOLVER & DECISION ENGINE CALCULATIONS
# ============================================================================
def default_ode(state, t, a, b, c, shock_val):
    x, y, z = state
    shock = shock_val if (0.45 * t_max <= t <= 0.55 * t_max) else 0.0
    dxdt = x - z - (y - a) * x + shock
    dydt = 1 - b * y - x ** 2
    dzdt = x - c * z
    return [dxdt, dydt, dzdt]

t = np.linspace(0, t_max, t_max * 10)
initial_state = [0.1, 0.1, 0.1]

def _solve(func, y0, t_arr, args=()):
    try:
        sol = odeint(func, y0, t_arr, args=args, mxstep=5000)
    except Exception:
        sol = np.zeros((len(t_arr), len(y0)))
    return np.clip(np.nan_to_num(sol), -1e4, 1e4)

solution = _solve(default_ode, initial_state, t, args=(a, b, c, policy_shock))
x_traj, y_traj, z_traj = solution[:, 0], solution[:, 1], solution[:, 2]

# Numerical Stability Metrics
perturbation_growth = np.abs(np.gradient(x_traj)) + 1e-5
mlce_heuristic = float(np.mean(np.log(perturbation_growth + 1e-5)) / (t[1] - t[0]))
max_volatility = float(np.std(x_traj))
risk_score = min(100.0, max(0.0, (mlce_heuristic + 0.5) * 40 + max_volatility * 15))

# Decision Recommendation Engine
if risk_score < 35.0:
    RECOMMENDATION = "INVEST / EXPAND"
    REC_COLOR = "status-invest"
    ACTION_SUMMARY = "High stability with low volatility. Favorable conditions to deploy capital, expand capacity, or commit long-term reserves."
elif risk_score < 65.0:
    RECOMMENDATION = "HOLD / MONITOR"
    REC_COLOR = "status-hold"
    ACTION_SUMMARY = "Moderate risk and systemic friction detected. Maintain current posture, rebalance liquidity, and hold buffer reserves."
else:
    RECOMMENDATION = "PULL BACK / DE-RISK"
    REC_COLOR = "status-pullback"
    ACTION_SUMMARY = "Critical stress signals detected. Reduce leverage, liquidate vulnerable positions, enforce bed/capacity preservation, and trigger risk contingencies."

# ============================================================================
# MAIN VIEW ROUTER
# ============================================================================
st.markdown('<div class="main-header-glow">Sovereign Real-Time Decision & Risk Engine</div>', unsafe_allow_html=True)
st.markdown(f"<b>Jurisdiction:</b> {target_country} ({specific_location}) &nbsp;|&nbsp; <b>Sector:</b> {sector_key} &nbsp;|&nbsp; <b>Analyst:</b> {author_name}", unsafe_allow_html=True)
st.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)

if "Decision & Action" in user_role:
    st.markdown("### ? Automated Real-Time Decision Intelligence")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Automated Action Trigger</div>
            <div style="margin-top:0.5rem;"><span class="status-indicator {REC_COLOR}">{RECOMMENDATION}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{risk_score:.1f} / 100</div>
            <div class="metric-label">Composite Risk Index</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{mlce_heuristic:.3f}</div>
            <div class="metric-label">Stability Index (mLCE)</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="glass-container">
        <h4>?? Sector Guidance Briefing � {sector_key}</h4>
        <p><b>Recommended Action:</b> {ACTION_SUMMARY}</p>
        <p><b>Location Scope:</b> {target_country} � {specific_location}</p>
        <p><b>Primary Vulnerability Drivers:</b> Growth Drive (a={a}), Operational Friction (b={b}), Reserve Depletion Buffer (c={c}).</p>
    </div>
    """, unsafe_allow_html=True)

    # Decision Visualization Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=x_traj, mode='lines', name='Sector Trajectory', line=dict(color='#60A5FA', width=2.5)))
    fig.add_trace(go.Scatter(x=t, y=y_traj, mode='lines', name='Cost / Stress Load', line=dict(color='#F87171', width=1.5, dash='dash')))
    fig.add_trace(go.Scatter(x=t, y=z_traj, mode='lines', name='Reserve Buffer', line=dict(color='#34D399', width=1.5)))
    fig.update_layout(title="Real-Time Sector Trajectory & Stress Projections", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400)
    st.plotly_chart(fig, use_container_width=True)

elif "Chat Command" in user_role:
    st.markdown("### 💬 Natural Language Command Core")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("Command or query decision triggers..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        reply = f"Decision Core Directive for {target_country} ({sector_key}): Recommended action is **{RECOMMENDATION}** (Risk Score: {risk_score:.1f}/100). {ACTION_SUMMARY}"
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"): st.markdown(reply)

elif "Executive Storyboard" in user_role:
    st.markdown("### ?? Executive Storyboard")
    fig3d = go.Figure(data=[go.Scatter3d(x=x_traj, y=y_traj, z=z_traj, mode='lines', line=dict(color='#60A5FA', width=4))])
    fig3d.update_layout(title="3D System Attractor Landscape", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=500)
    st.plotly_chart(fig3d, use_container_width=True)

elif "Real-Time Data Ingestion" in user_role:
    st.markdown("### ?? External Data Ingestion Pipeline")
    up_file = st.file_uploader("Upload CSV, JSON, or Excel Dataset for Sector Calibration", type=["csv", "json", "xlsx", "xls", "txt"])
    if up_file:
        df = _load_any(up_file)
        if df is not None:
            st.success(f"Loaded {up_file.name} with {len(df)} records.")
            st.dataframe(df.head(10), use_container_width=True)

elif "Directory" in user_role:
    st.markdown("### ?? Institutional Directory")
    cursor = db_conn.cursor()
    cursor.execute("SELECT analyst_name, org_email, contact_phone, clearance_level, primary_sector FROM analyst_contacts")
    st.dataframe(pd.DataFrame(cursor.fetchall(), columns=["Name", "Email", "Phone", "Clearance", "Domain"]), use_container_width=True)

else:
    st.markdown("### ?? Operational Risk & Analytics")
    st.info(f"System State: {RECOMMENDATION} | Risk Index: {risk_score:.2f} | Stability Index: {mlce_heuristic:.4f}")

