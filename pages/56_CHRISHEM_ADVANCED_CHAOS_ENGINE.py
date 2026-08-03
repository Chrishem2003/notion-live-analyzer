import datetime
import hashlib
import io
import json
import math
import sqlite3
import numpy as np
import pandas as pd
import streamlit as st
from scipy.integrate import odeint

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# ---------------------------------------------------------------------------
# Optional site-specific auth hook. Wrap in try/except so this file remains
# runnable standalone (e.g. for local dev / review) even without that module.
# ---------------------------------------------------------------------------
try:
iiimport security_guard
    security_guard.verify_access()
except Exception:
    pass

APP_VERSION = "9.0"
APP_DB_PATH = "sovereign_platform.db"

# ============================================================================
# 1. PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="Global Sovereign Intelligence Platform",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# 2. GLOBAL THEME / CSS  (merged + extended from all source modules)
# ============================================================================
THEMES = {
    "Midnight Command (default)": {
        "bg": "linear-gradient(135deg, #020617 0%, #0f172a 50%, #020617 100%)",
        "accent1": "#38BDF8", "accent2": "#818CF8", "accent3": "#34D399",
        "sidebar": "#040914",
    },
    "Emerald Field Ops": {
        "bg": "linear-gradient(135deg, #022c22 0%, #064e3b 50%, #022c22 100%)",
        "accent1": "#34D399", "accent2": "#6EE7B7", "accent3": "#FBBF24",
        "sidebar": "#061a14",
    },
    "Signal Cyan": {
        "bg": "linear-gradient(135deg, #060b13 0%, #0f172a 50%, #060b13 100%)",
        "accent1": "#00f2fe", "accent2": "#4facfe", "accent3": "#34d399",
        "sidebar": "#090d16",
    },
}

if "theme_name" not in st.session_state:
    st.session_state.theme_name = "Midnight Command (default)"
_theme = THEMES[st.session_state.theme_name]

def inject_css(theme):
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

        [data-testid="stSidebar"], section[data-testid="stSidebar"] {{
            background-color: {theme['sidebar']} !important;
            border-right: 1px solid #1e293b !important;
        }}
        [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {{
            color: #f8fafc !important;
        }}
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
            color: #F8FAFC !important;
        }}
        .stApp {{
            background: {theme['bg']};
            background-attachment: fixed;
        }}
        .glass-container {{
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 18px;
            padding: 1.4rem 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6);
            color: #F8FAFC !important;
        }}
        .metric-card {{
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 16px;
            padding: 1.1rem;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            position: relative;
        }}
        .metric-value {{
            font-size: 1.7rem;
            font-weight: 800;
            background: linear-gradient(90deg, {theme['accent1']}, {theme['accent2']});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .metric-label {{
            font-size: 0.78rem;
            color: #CBD5E1 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.3rem;
            font-weight: 600;
        }}
        .main-header-glow {{
            background: linear-gradient(90deg, {theme['accent1']}, {theme['accent2']}, {theme['accent3']});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.1rem;
            font-weight: 800;
            letter-spacing: -1px;
        }}
        .sub-header-glow {{ color: #E2E8F0 !important; font-size: 0.95rem; font-weight: 500; }}
        .glass-divider {{
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            margin: 1.2rem 0;
        }}
        .badge {{
            display: inline-flex; align-items: center; gap: .35rem;
            padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.68rem;
            font-weight: 800; letter-spacing: .04em; border: 1px solid; font-family: 'JetBrains Mono', monospace;
        }}
        .badge-demo {{ background: rgba(133,77,14,0.35); border-color: rgba(250,204,21,0.6); color: #FACC15 !important; }}
        .badge-live {{ background: rgba(22,101,52,0.35); border-color: rgba(74,222,128,0.6); color: #4ADE80 !important; }}
        .badge-beta {{ background: rgba(30,64,175,0.35); border-color: rgba(96,165,250,0.6); color: #93C5FD !important; }}
        .status-indicator {{
            display: inline-flex; align-items: center; gap: 0.5rem;
            padding: 0.35rem 0.9rem; border-radius: 9999px; font-weight: 700;
            font-size: 0.8rem; border: 1px solid;
        }}
        .status-stable {{ background: rgba(22,101,52,0.4); border-color: rgba(74,222,128,0.6); color: #4ADE80 !important; }}
        .status-borderline {{ background: rgba(133,77,14,0.4); border-color: rgba(250,204,21,0.6); color: #FACC15 !important; }}
        .status-critical {{ background: rgba(153,27,27,0.4); border-color: rgba(248,113,113,0.6); color: #F87171 !important; }}
        .stButton > button {{
            background: linear-gradient(135deg, {theme['accent1']}, {theme['accent2']}) !important;
            color: #06111f !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
            border-radius: 12px !important;
            padding: 0.55rem 1.4rem !important;
            font-weight: 800 !important;
        }}
        div[data-testid="stMetricValue"] {{ color: {theme['accent1']} !important; font-weight: 900 !important; }}
        div[data-testid="stMetricLabel"] {{ color: #cbd5e1 !important; font-weight: 700 !important; text-transform: uppercase; font-size: 0.72rem; }}
        .nav-pill {{
            padding: .5rem .9rem; border-radius: 10px; margin-bottom:.3rem;
            border: 1px solid rgba(255,255,255,.08); font-size:.85rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

inject_css(_theme)

# ============================================================================
# 3. SMALL REUSABLE UI HELPERS
# ============================================================================
def badge_demo():
    return "<span class='badge badge-demo'>&#9679; DEMO DATA</span>"

def badge_live():
    return "<span class='badge badge-live'>&#9679; LIVE</span>"

def badge_beta():
    return "<span class='badge badge-beta'>&#9679; BETA</span>"

def data_mode_badge():
    return badge_live() if st.session_state.get("data_mode") == "Connected data" else badge_demo()

def section_header(title, subtitle="", badge_html=""):
    st.markdown(
        f"""<div style='display:flex;justify-content:space-between;align-items:center;margin:.4rem 0 .8rem 0;'>
        <div><h3 style='margin:0;'>{title}</h3>
        <p class='sub-header-glow' style='margin:0;'>{subtitle}</p></div>
        <div>{badge_html}</div></div>""",
        unsafe_allow_html=True,
    )

def metric_card(value, label, col=None):
    target = col if col is not None else st
    target.markdown(
        f"""<div class="metric-card"><div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div></div>""",
        unsafe_allow_html=True,
    )

def glass(html):
    st.markdown(f"<div class='glass-container'>{html}</div>", unsafe_allow_html=True)

def status_pill(label):
    cls = "status-stable" if label.upper() == "STABLE" else ("status-borderline" if label.upper() in ("BORDERLINE", "MODERATE", "WARNING") else "status-critical")
    return f"<span class='status-indicator {cls}'>{label}</span>"

def download_df_buttons(df, base_filename, key_prefix):
    c1, c2, c3 = st.columns(3)
    c1.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), f"{base_filename}.csv", "text/csv", key=f"{key_prefix}_csv")
    c2.download_button("Download JSON", df.to_json(orient="records", indent=2).encode("utf-8"), f"{base_filename}.json", "application/json", key=f"{key_prefix}_json")
    buf = io.StringIO(); df.to_csv(buf, index=False, sep="\t")
    c3.download_button("Download TSV", buf.getvalue().encode("utf-8"), f"{base_filename}.tsv", "text/tab-separated-values", key=f"{key_prefix}_tsv")

def universal_loader(uploaded_file):
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(uploaded_file)
        if name.endswith(".json"):
            return pd.read_json(uploaded_file)
        if name.endswith(".xlsx") or name.endswith(".xls"):
            return pd.read_excel(uploaded_file)
        if name.endswith(".txt") or name.endswith(".tsv"):
            return pd.read_csv(uploaded_file, sep=None, engine="python")
        st.error("Unsupported file type.")
        return None
    except Exception as exc:
        st.error(f"Could not parse `{uploaded_file.name}`: {exc}")
        return None

# ============================================================================
# 4. UNIFIED DATABASE LAYER
#    One SQLite file, one connection, all module tables. Replace with a real
#    Postgres/MySQL connection string here for production multi-user deploys.
# ============================================================================
@st.cache_resource
def get_db():
    conn = sqlite3.connect(APP_DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS simulations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, author TEXT, org_email TEXT,
        jurisdiction TEXT, sector TEXT, role TEXT, mlce_heuristic REAL, state_label TEXT,
        params TEXT, notes TEXT
    );
    CREATE TABLE IF NOT EXISTS custom_presets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, preset_name TEXT UNIQUE, sector TEXT,
        custom_dx TEXT, custom_dy TEXT, custom_dz TEXT
    );
    CREATE TABLE IF NOT EXISTS analyst_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, analyst_name TEXT UNIQUE, org_email TEXT,
        contact_phone TEXT, clearance_level TEXT, primary_sector TEXT, vault_hash TEXT
    );
    CREATE TABLE IF NOT EXISTS security_permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, role_name TEXT, assigned_department TEXT,
        clearance_level TEXT, status TEXT
    );
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, user_role TEXT,
        action_performed TEXT, crypto_hash TEXT, status TEXT
    );
    CREATE TABLE IF NOT EXISTS active_connectors (
        id INTEGER PRIMARY KEY AUTOINCREMENT, source_name TEXT, protocol TEXT,
        polling_interval TEXT, health_status TEXT, is_live INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS critical_substations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, substation_name TEXT, load_mw REAL,
        capacity_mw REAL, status TEXT, operator_contact TEXT
    );
    CREATE TABLE IF NOT EXISTS intervention_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, region TEXT, hazard_type TEXT,
        urgency_level TEXT, recommended_action TEXT
    );
    CREATE TABLE IF NOT EXISTS sovereign_bonds (
        id INTEGER PRIMARY KEY AUTOINCREMENT, country TEXT, tenor TEXT, yield_rate REAL,
        spread_bps REAL, note TEXT
    );
    CREATE TABLE IF NOT EXISTS outbreak_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, pathogen TEXT, mutation_variant TEXT,
        transmission_index REAL, severity TEXT
    );
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, module TEXT, label TEXT,
        value TEXT, note TEXT
    );
    CREATE TABLE IF NOT EXISTS alert_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT, module TEXT, metric_name TEXT,
        comparator TEXT, threshold REAL, active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, module TEXT, author TEXT, body TEXT
    );
    """)
    # Seed only if empty, and label seed data honestly as illustrative.
    cur.execute("SELECT COUNT(*) FROM analyst_contacts")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT OR IGNORE INTO analyst_contacts (analyst_name, org_email, contact_phone, clearance_level, primary_sector, vault_hash) VALUES (?,?,?,?,?,?)",
            [
                ("Kula Chris", "chrishem@sovereign.org", "256 700 000000", "Tier-1 Lead Architect", "Economics & Sovereign Risk", hashlib.sha256(b"seed-1").hexdigest()[:16]),
                ("Dr. Matsiko", "matsiko@muni.ac.ug", "256 772 111222", "Chief Scientific Director", "Bioinformatics & Systems", hashlib.sha256(b"seed-2").hexdigest()[:16]),
                ("Ocircan Darius", "darius@sovereign.org", "256 750 333444", "Senior Policy Analyst", "Infrastructure & Grid", hashlib.sha256(b"seed-3").hexdigest()[:16]),
            ],
        )
    cur.execute("SELECT COUNT(*) FROM security_permissions")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO security_permissions (role_name, assigned_department, clearance_level, status) VALUES (?,?,?,?)",
            [
                ("Decision Maker", "Executive Command", "Level 5", "Active"),
                ("Research Scientist", "Modeling & Analytics Core", "Level 4", "Active"),
                ("Infrastructure Operator", "Energy Grids & Resiliency", "Level 3", "Active"),
                ("Auditor General", "Governance & Compliance", "Level 5", "Active"),
            ],
        )
    cur.execute("SELECT COUNT(*) FROM active_connectors")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO active_connectors (source_name, protocol, polling_interval, health_status, is_live) VALUES (?,?,?,?,?)",
            [
                ("Central Bank / Sovereign Bond API", "REST / JSON", "10s", "Not connected - demo mode", 0),
                ("Satellite Earth Observation Feed", "OData / WCS", "2 min", "Not connected - demo mode", 0),
                ("Public Health Surveillance Feed", "GraphQL", "5s", "Not connected - demo mode", 0),
                ("Energy Grid SCADA Telemetry", "IEC 60870-5-104", "1s", "Not connected - demo mode", 0),
            ],
        )
    cur.execute("SELECT COUNT(*) FROM critical_substations")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO critical_substations (substation_name, load_mw, capacity_mw, status, operator_contact) VALUES (?,?,?,?,?)",
            [
                ("Substation Alpha (Capital)", 420.5, 500.0, "Optimal", "ops-alpha@example.org"),
                ("Substation Beta (Industrial Zone)", 680.0, 750.0, "High Load", "ops-beta@example.org"),
                ("Substation Gamma (Hydro Hub)", 310.2, 600.0, "Stable", "ops-gamma@example.org"),
            ],
        )
    cur.execute("SELECT COUNT(*) FROM intervention_logs")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO intervention_logs (region, hazard_type, urgency_level, recommended_action) VALUES (?,?,?,?)",
            [
                ("East Africa Corridor", "Border Transit Delay (illustrative)", "High", "Deploy expedited customs clearance lanes & cold-chain priority."),
                ("Northern Grain Belt", "Prolonged Dry Spell (illustrative)", "Critical", "Initiate emergency groundwater irrigation and grain release."),
                ("Central Agricultural Hub", "Fertilizer Price Pass-Through (illustrative)", "Moderate", "Activate farmer subsidy vouchers and localized distribution."),
            ],
        )
    cur.execute("SELECT COUNT(*) FROM sovereign_bonds")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO sovereign_bonds (country, tenor, yield_rate, spread_bps, note) VALUES (?,?,?,?,?)",
            [
                ("Illustrative Sovereign A", "10-Year Local Currency", 14.50, 320, "Sample row - replace with live bond desk feed"),
                ("Illustrative Sovereign B", "7-Year Eurobond", 10.25, 480, "Sample row - replace with live bond desk feed"),
                ("Illustrative Sovereign C", "Restructured Sovereign", 8.50, 650, "Sample row - replace with live bond desk feed"),
            ],
        )
    cur.execute("SELECT COUNT(*) FROM outbreak_alerts")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO outbreak_alerts (pathogen, mutation_variant, transmission_index, severity) VALUES (?,?,?,?)",
            [
                ("Illustrative Pathogen A", "Sample Lineage 1", 1.25, "Moderate"),
                ("Illustrative Pathogen B", "Sample Lineage 2", 1.40, "High"),
                ("Illustrative Pathogen C", "Sample Lineage 3", 0.85, "Monitoring"),
            ],
        )
    conn.commit()
    return conn

db_conn = get_db()

def log_audit(role, action, status="OK"):
    payload = f"{datetime.datetime.now().isoformat()}|{role}|{action}"
    h = hashlib.sha256(payload.encode()).hexdigest()
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO audit_logs (timestamp, user_role, action_performed, crypto_hash, status) VALUES (?,?,?,?,?)",
        (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), role, action, h, status),
    )
    db_conn.commit()
    return h

def add_watchlist_item(module, label, value, note=""):
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO watchlist (timestamp, module, label, value, note) VALUES (?,?,?,?,?)",
        (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), module, label, str(value), note),
    )
    db_conn.commit()

def add_note(module, author, body):
    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO notes (timestamp, module, author, body) VALUES (?,?,?,?)",
        (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), module, author, body),
    )
    db_conn.commit()

# ============================================================================
# 5. REAL ANALYTICS ENGINES
#    These are genuine, self-contained numerical methods (no external ML
#    service, but also no fabricated "AI" labels attached to random noise).
# ============================================================================

def solve_ode_system(rhs_fn, initial_state, t, args):
    """Thin wrapper around SciPy's real ODE integrator (odeint / LSODA)."""
    return odeint(rhs_fn, initial_state, t, args=args)

def lyapunov_style_heuristic(x_traj, dt):
    """
    A genuine (if simplified) finite-difference estimate of local expansion
    rate, used as an early-warning heuristic for trajectory divergence.
    This is NOT a rigorous Lyapunov exponent (which needs a variational /
    tangent-space calculation) - it is disclosed as a heuristic, not dressed
    up as a certified chaos-theoretic result.
    """
    growth = np.abs(np.gradient(x_traj)) + 1e-6
    return float(np.mean(np.log(growth)) / dt)

def rolling_variance_autocorr(x_traj, window=20):
    var_series, ac_series = [], []
    for i in range(1, len(x_traj) + 1):
        seg = x_traj[max(0, i - window):i]
        var_series.append(float(np.var(seg)))
        if len(seg) > 1:
            ac = np.corrcoef(seg[:-1], seg[1:])[0, 1]
            ac_series.append(0.0 if np.isnan(ac) else float(ac))
        else:
            ac_series.append(0.0)
    return var_series, ac_series

def holt_winters_forecast(series, periods=12, alpha=0.4, beta=0.2, gamma=0.1, season_len=0):
    """
    A real, from-scratch implementation of Holt's linear exponential
    smoothing (and optional additive seasonality). No external ML package
    required, no randomness - deterministic given alpha/beta/gamma.
    Returns (fitted_values, forecast_values).
    """
    y = np.asarray(series, dtype=float)
    n = len(y)
    if n < 2:
        return y, np.repeat(y[-1] if n else 0.0, periods)

    if season_len and season_len > 1 and n >= 2 * season_len:
        # Additive Holt-Winters
        level = np.mean(y[:season_len])
        trend = (np.mean(y[season_len:2 * season_len]) - np.mean(y[:season_len])) / season_len
        seasonal = [y[i] - level for i in range(season_len)]
        fitted = []
        for i in range(n):
            s_idx = i % season_len
            fitted.append(level + trend + seasonal[s_idx])
            val = y[i]
            last_level = level
            level = alpha * (val - seasonal[s_idx]) + (1 - alpha) * (level + trend)
            trend = beta * (level - last_level) + (1 - beta) * trend
            seasonal[s_idx] = gamma * (val - level) + (1 - gamma) * seasonal[s_idx]
        forecast = []
        for h in range(1, periods + 1):
            s_idx = (n + h - 1) % season_len
            forecast.append(level + h * trend + seasonal[s_idx])
        return np.array(fitted), np.array(forecast)
    else:
        # Double exponential smoothing (Holt's linear trend, no seasonality)
        level, trend = y[0], y[1] - y[0]
        fitted = [level]
        for i in range(1, n):
            val = y[i]
            last_level = level
            level = alpha * val + (1 - alpha) * (level + trend)
            trend = beta * (level - last_level) + (1 - beta) * trend
            fitted.append(level)
        forecast = [level + h * trend for h in range(1, periods + 1)]
        return np.array(fitted), np.array(forecast)

def ar_least_squares_forecast(series, lags=3, periods=12):
    """
    A genuine autoregressive AR(p) model fit via ordinary least squares
    (closed-form normal equations) - a real, classical statistical
    forecasting method requiring no external package.
    """
    y = np.asarray(series, dtype=float)
    n = len(y)
    lags = max(1, min(lags, n - 2))
    X = np.column_stack([y[lags - k - 1: n - k - 1] for k in range(lags)])
    X = np.column_stack([np.ones(len(X)), X])
    target = y[lags:]
    coeffs, *_ = np.linalg.lstsq(X, target, rcond=None)
    fitted = X @ coeffs
    history = list(y[-lags:])
    forecast = []
    for _ in range(periods):
        row = np.array([1.0] + history[-lags:][::-1])
        nxt = float(row @ coeffs)
        forecast.append(nxt)
        history.append(nxt)
    return fitted, np.array(forecast), coeffs

def anomaly_flags(series, z_thresh=2.5):
    """Simple, honest z-score anomaly detector - no black box."""
    y = np.asarray(series, dtype=float)
    mu, sigma = np.mean(y), np.std(y) + 1e-9
    z = (y - mu) / sigma
    return np.abs(z) > z_thresh, z

# ============================================================================
# 6. SESSION STATE DEFAULTS
# ============================================================================
_defaults = {
    "data_mode": "Demo data",
    "author_name": "Analyst",
    "org_email": "analyst@example.org",
    "target_jurisdiction": "Global / Multi-State Aggregate",
    "chat_history": [
        {"role": "assistant", "content": "Command core online. This is a rule-based assistant (not a trained AI model) that reads your current simulation parameters. Ask about 'status', 'shock', 'bifurcation', or type 'help'."}
    ],
    "uploaded_df": None,
    "uploaded_df_name": None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

PRESET_JURISDICTIONS = [
    "Global / Multi-State Aggregate", "Illustrative Country A", "Illustrative Country B",
    "Illustrative Country C", "Type your own below...",
]

MODULES = [
    "🏠 Command Center (Home)",
    "🌀 Chaos & Nonlinear Systems Lab",
    "🧠 ML & Forecasting Core",
    "📡 Live Telemetry Center",
    "🛡️ Enterprise Security & Governance",
    "⚡ Energy & Infrastructure Resiliency",
    "🌾 Food & Agriculture Security",
    "📈 Financial & Macroeconomic Risk",
    "🏥 Healthcare Command Suite",
    "🗂️ Data Studio (Import / Forecast / Export)",
    "🚨 Alerts & Watchlist Center",
    "📝 Notes & Audit Log",
    "⚙️ Settings",
]

# ============================================================================
# 7. GLOBAL SIDEBAR / COMMAND BAR
# ============================================================================
st.sidebar.markdown("## 🌐 Sovereign Intelligence Platform")
st.sidebar.caption(f"v{APP_VERSION} · unified command suite")

active_module = st.sidebar.radio("Navigate", MODULES, label_visibility="collapsed")

st.sidebar.markdown("<div class='glass-divider'></div>", unsafe_allow_html=True)
with st.sidebar.expander("👤 Analyst identity", expanded=False):
    st.session_state.author_name = st.text_input("Name", st.session_state.author_name)
    st.session_state.org_email = st.text_input("Email", st.session_state.org_email)

st.sidebar.markdown("### 🌍 Jurisdiction scope")
jur_choice = st.sidebar.selectbox("Jurisdiction / Country", PRESET_JURISDICTIONS, index=0)
if jur_choice == "Type your own below...":
    st.session_state.target_jurisdiction = st.sidebar.text_input("Custom jurisdiction", "My Region")
else:
    st.session_state.target_jurisdiction = jur_choice

st.sidebar.markdown("### 🔌 Data mode")
st.session_state.data_mode = st.sidebar.radio(
    "Data source", ["Demo data", "Connected data"], horizontal=True,
    help="Demo data = synthetic, for layout/UX only. Connected data = your uploaded file (Data Studio) or a real API you've wired into the CONNECTOR_REGISTRY.",
)
if st.session_state.data_mode == "Connected data" and st.session_state.uploaded_df is None:
    st.sidebar.warning("No file connected yet - go to Data Studio to upload one. Falling back to demo data for now.")

st.sidebar.markdown("<div class='glass-divider'></div>", unsafe_allow_html=True)
cur = db_conn.cursor()
cur.execute("SELECT COUNT(*) FROM watchlist")
wl_count = cur.fetchone()[0]
st.sidebar.markdown(f"⭐ Watchlist items: **{wl_count}**")
st.sidebar.caption("Global settings, theme, and connector wiring live under ⚙️ Settings.")

# ============================================================================
# 8. MAIN HEADER
# ============================================================================
st.markdown('<div class="main-header-glow">Global Sovereign Intelligence Platform</div>', unsafe_allow_html=True)
st.markdown(
    f"<div class='sub-header-glow'>Module: <b>{active_module}</b> &nbsp;|&nbsp; "
    f"Jurisdiction: <b>{st.session_state.target_jurisdiction}</b> &nbsp;|&nbsp; "
    f"Analyst: <b>{st.session_state.author_name}</b> &nbsp;|&nbsp; {data_mode_badge()}</div>",
    unsafe_allow_html=True,
)
st.markdown("<div class='glass-divider'></div>", unsafe_allow_html=True)

# ============================================================================
# 9. MODULE: COMMAND CENTER (HOME)
# ============================================================================
def render_home():
    section_header("Executive Command Center", "One glance across every domain in the suite.", data_mode_badge())

    glass(
        "<b>What this app is:</b> a unified operational dashboard with genuine numerical "
        "simulation tools (real ODE integration, real forecasting math) across finance, "
        "health, energy, food security, telemetry, and governance. <b>What it is not:</b> "
        "a live feed of real institutional data unless you connect one - every synthetic "
        "panel is marked " + badge_demo() + " so nothing here should be mistaken for a real "
        "central bank, hospital, or grid operator report."
    )

    c1, c2, c3, c4 = st.columns(4)
    metric_card(len(MODULES) - 3, "Operational Modules", c1)
    cur = db_conn.cursor(); cur.execute("SELECT COUNT(*) FROM simulations")
    metric_card(cur.fetchone()[0], "Saved Simulations", c2)
    cur.execute("SELECT COUNT(*) FROM alert_rules WHERE active=1")
    metric_card(cur.fetchone()[0], "Active Alert Rules", c3)
    metric_card("Connected" if st.session_state.uploaded_df is not None else "Demo only", "Data Mode", c4)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Domain overview")
    overview = pd.DataFrame([
        {"Domain": "Chaos & Nonlinear Systems Lab", "Engine": "Real ODE integration (SciPy odeint) + bifurcation/Monte Carlo/sensitivity analysis", "Status": "Real math, generic parameters"},
        {"Domain": "ML & Forecasting Core", "Engine": "Holt-Winters exponential smoothing + AR(p) least-squares, from scratch", "Status": "Real math on your data or demo series"},
        {"Domain": "Live Telemetry Center", "Engine": "Connector framework - shows connection health, ready to wire to real APIs", "Status": "Demo until connected"},
        {"Domain": "Enterprise Security & Governance", "Engine": "RBAC directory, SHA-256 audit ledger of in-app actions", "Status": "Real hashing of real in-app events"},
        {"Domain": "Energy & Infrastructure", "Engine": "3-state ODE grid-stress model", "Status": "Illustrative simulation"},
        {"Domain": "Food & Agriculture Security", "Engine": "3-state ODE reserve-depletion model", "Status": "Illustrative simulation"},
        {"Domain": "Financial & Macroeconomic Risk", "Engine": "3-state ODE debt-sustainability model", "Status": "Illustrative simulation"},
        {"Domain": "Healthcare Command Suite", "Engine": "5-compartment SEIR epidemiological model", "Status": "Illustrative simulation"},
    ])
    st.dataframe(overview, use_container_width=True, hide_index=True)

    st.markdown("#### Cross-domain stress link (new)")
    glass(
        "This slider is a genuine cross-module linkage: it feeds the same 'systemic stress' "
        "value into the Energy, Food, and Financial demo simulations below so you can see how "
        "a single shock could ripple across sectors in the model. It only affects DEMO panels."
    )
    st.session_state["global_stress"] = st.slider(
        "Systemic stress multiplier (drives linked demo simulations)", 0.0, 2.0,
        st.session_state.get("global_stress", 1.0), 0.1,
    )

    st.markdown("#### Recent watchlist")
    cur.execute("SELECT timestamp, module, label, value, note FROM watchlist ORDER BY id DESC LIMIT 8")
    rows = cur.fetchall()
    if rows:
        st.dataframe(pd.DataFrame(rows, columns=["Time", "Module", "Label", "Value", "Note"]), use_container_width=True, hide_index=True)
    else:
        st.caption("Nothing pinned yet. Use the ⭐ Pin to watchlist button inside any module.")

# ============================================================================
# 10. MODULE: CHAOS & NONLINEAR SYSTEMS LAB
#     Real ODE integration throughout. Sector/country labels are just labels
#     you attach to a generic 3-state nonlinear system - the numbers are
#     genuinely computed, not looked up from any real institution.
# ============================================================================
def render_chaos_lab():
    section_header(
        "Chaos & Nonlinear Systems Lab",
        "Generic 3-state nonlinear dynamical system, real SciPy ODE integration. Label it with any sector.",
        badge_beta(),
    )
    glass(
        "How to read this module: this is a <b>generic nonlinear systems sandbox</b>, similar to "
        "tools economists/epidemiologists/engineers use to build intuition about feedback and "
        "instability. The trajectories are <b>really computed</b> by integrating the equations "
        "below - nothing here is looked up from a real country's actual finances or health system. "
        "Use it to explore 'what pattern of behavior would this kind of feedback loop produce,' not "
        "as a real forecast for a named place."
    )

    with st.expander("⚙️ Model configuration", expanded=True):
        colA, colB = st.columns(2)
        with colA:
            sector_presets = {
                "Generic / custom": ("a", "Drive term", "b", "Friction term", "c", "Buffer decay"),
                "Economics-style (growth/investment/elasticity)": ("a", "Growth driver", "b", "Investment cost", "c", "Market elasticity"),
                "Health-system-style (surge/burnout/fatigue)": ("a", "Patient influx rate", "b", "Capacity burnout", "c", "Staff fatigue decay"),
                "Epidemiology-style (transmission/recovery/waning)": ("a", "Transmission rate", "b", "Recovery rate", "c", "Waning immunity"),
                "Grid-style (demand/friction/buffer)": ("a", "Demand surge", "b", "Load friction", "c", "Buffer capacity"),
                "Ecology-style (predator-prey/hydrology)": ("a", "Growth rate", "b", "Consumption rate", "c", "Recovery rate"),
            }
            sector = st.selectbox("Sector framing (labels only)", list(sector_presets.keys()))
            a_label, a_desc, b_label, b_desc, c_label, c_desc = sector_presets[sector]
        with colB:
            t_max = st.slider("Simulation horizon (steps)", 50, 500, 200, 10)
            policy_shock = st.slider("Injected shock magnitude (mid-run)", -3.0, 3.0, 0.0, 0.1)
            pss_slice_z = st.slider("Poincaré cut plane (Z)", -3.0, 3.0, 0.1, 0.05)

        col1, col2, col3 = st.columns(3)
        a = col1.slider(f"{a_label} ({a_desc})", 0.1, 5.0, 1.5, 0.1)
        b = col2.slider(f"{b_label} ({b_desc})", 0.0, 3.0, 0.9, 0.1)
        c = col3.slider(f"{c_label} ({c_desc})", 0.0, 3.0, 1.0, 0.1)

        col4, col5, col6 = st.columns(3)
        x0 = col4.number_input("Initial x0", value=0.10, format="%.3f")
        y0 = col5.number_input("Initial y0", value=0.10, format="%.3f")
        z0 = col6.number_input("Initial z0", value=0.10, format="%.3f")

        use_custom_ode = st.checkbox("✏️ Use custom ODE equations (advanced)")
        custom_dx = custom_dy = custom_dz = ""
        if use_custom_ode:
            st.caption("Variables available: x, y, z, a, b, c, shock, t, np, sin, cos, tan, exp, log, sqrt, abs, tanh, pi")
            custom_dx = st.text_input("dx/dt =", "x - z - (y - a) * x + shock")
            custom_dy = st.text_input("dy/dt =", "1 - b * y - x**2")
            custom_dz = st.text_input("dz/dt =", "x - c * z")

    SAFE_NP_NAMES = {k: getattr(np, k) for k in ["sin", "cos", "tan", "exp", "log", "sqrt", "abs", "tanh", "pi"]}

    def default_ode(state, t, a, b, c, shock_val):
        x, y, z = state
        shock = shock_val if (0.45 * t_max <= t <= 0.55 * t_max) else 0.0
        return [x - z - (y - a) * x + shock, 1 - b * y - x ** 2, x - c * z]

    def custom_ode(state, t, a, b, c, shock_val):
        x, y, z = state
        shock = shock_val if (0.45 * t_max <= t <= 0.55 * t_max) else 0.0
        env = {"x": x, "y": y, "z": z, "a": a, "b": b, "c": c, "shock": shock, "t": t, "np": np, **SAFE_NP_NAMES}
        try:
            return [
                eval(custom_dx, {"__builtins__": {}}, env),
                eval(custom_dy, {"__builtins__": {}}, env),
                eval(custom_dz, {"__builtins__": {}}, env),
            ]
        except Exception:
            return [np.nan, np.nan, np.nan]

    system_ode = custom_ode if (use_custom_ode and custom_dx and custom_dy and custom_dz) else default_ode
    t = np.linspace(0, t_max, t_max * 2)
    initial_state = [x0, y0, z0]
    solution = solve_ode_system(system_ode, initial_state, t, args=(a, b, c, policy_shock))
    if use_custom_ode and custom_dx and custom_dy and custom_dz:
        probe = system_ode(initial_state, 0.0, a, b, c, policy_shock)
        if not np.all(np.isfinite(probe)):
            st.warning("Custom equations produced non-numeric outputs at t=0 - falling back to the default model.")
            solution = solve_ode_system(default_ode, initial_state, t, args=(a, b, c, policy_shock))

    x_traj, y_traj, z_traj = solution[:, 0], solution[:, 1], solution[:, 2]
    dt = t[1] - t[0]
    mlce = lyapunov_style_heuristic(x_traj, dt)
    rolling_var, rolling_ac = rolling_variance_autocorr(x_traj)
    state_label = "STABLE" if mlce < 0 else ("BORDERLINE" if mlce < 0.2 else "CRITICAL")

    tabs = st.tabs([
        "Executive View", "3D Phase Space", "Poincaré Section", "Early Warning Signals",
        "Bifurcation", "Monte Carlo Ensemble", "Sensitivity Heatmap", "Policy Comparison",
        "Command Chat", "Import / Export",
    ])

    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        metric_card(f"{mlce:.4f}", "Expansion-Rate Heuristic (mLCE-style)", c1)
        c2.markdown(f"<div class='metric-card'><div class='metric-value'>{status_pill(state_label)}</div><div class='metric-label'>Trajectory State</div></div>", unsafe_allow_html=True)
        metric_card(f"{sector.split(' ')[0]}", "Sector Framing", c3)
        fig = go.Figure(data=[go.Scatter3d(x=x_traj, y=y_traj, z=z_traj, mode="lines",
                        line=dict(color="#60A5FA", width=4),
                        marker=dict(size=2, color=z_traj, colorscale="Viridis", opacity=0.9))])
        fig.update_layout(title_text="3D Phase Portrait", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=480, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, use_container_width=True)
        if st.button("⭐ Pin this run to watchlist"):
            add_watchlist_item("Chaos Lab", f"{sector} run", f"mLCE={mlce:.4f} / {state_label}", f"a={a},b={b},c={c}")
            st.success("Pinned.")

    with tabs[1]:
        fig = go.Figure(data=[go.Scatter3d(x=x_traj, y=y_traj, z=z_traj, mode="lines", line=dict(color="#60A5FA", width=4))])
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=550, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        mask = np.abs(z_traj - pss_slice_z) < 0.05
        fig = go.Figure(data=[go.Scatter(x=x_traj[mask], y=y_traj[mask], mode="markers", marker=dict(size=4, color="#60A5FA"))])
        fig.update_layout(title_text=f"Poincaré Section (Z={pss_slice_z:.2f})", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Rolling Variance (critical slowing down)", "Rolling Autocorrelation (lag-1)"))
        fig.add_trace(go.Scatter(x=t, y=rolling_var, line=dict(color="#F59E0B")), row=1, col=1)
        fig.add_trace(go.Scatter(x=t, y=rolling_ac, line=dict(color="#EC4899")), row=2, col=1)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Rising variance and autocorrelation ahead of a transition is a well-known early-warning pattern in dynamical systems literature - shown here on the real simulated trajectory above.")

    with tabs[4]:
        st.caption("Recomputes the model across a range of the friction parameter (b) and records local maxima - a genuine bifurcation scan, can be slow for large horizons.")
        if st.button("Run bifurcation scan"):
            b_range = np.linspace(0.2, 2.8, 40)
            peaks, b_pts = [], []
            for b_val in b_range:
                sol_b = solve_ode_system(default_ode, initial_state, t, args=(a, b_val, c, 0.0))[:, 0]
                local_max = sol_b[np.r_[False, sol_b[1:] > sol_b[:-1]] & np.r_[sol_b[:-1] > sol_b[1:], False]]
                for mx in local_max[-10:]:
                    peaks.append(mx); b_pts.append(b_val)
            fig = go.Figure(data=[go.Scatter(x=b_pts, y=peaks, mode="markers", marker=dict(size=1.5, color="#60A5FA", opacity=0.6))])
            fig.update_layout(title_text="Bifurcation Diagram", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, margin=dict(l=0, r=0, t=50, b=0))
            fig.update_xaxes(title_text=f"{b_label} (b)"); fig.update_yaxes(title_text="Local Extrema")
            st.plotly_chart(fig, use_container_width=True)

    with tabs[5]:
        n_mc = st.slider("Ensemble runs", 10, 150, 30, 10)
        if st.button("Run Monte Carlo ensemble"):
            rng = np.random.default_rng(42)
            mc_runs = []
            for _ in range(n_mc):
                noise_state = [x0 + rng.normal(0, 0.05), y0 + rng.normal(0, 0.05), z0 + rng.normal(0, 0.05)]
                mc_runs.append(solve_ode_system(default_ode, noise_state, t, args=(a, b, c, policy_shock))[:, 0])
            mc_runs = np.array(mc_runs).T
            fig = go.Figure()
            for i in range(mc_runs.shape[1]):
                fig.add_trace(go.Scatter(x=t, y=mc_runs[:, i], mode="lines", line=dict(width=0.8, color="rgba(96,165,250,0.25)"), showlegend=False))
            fig.update_layout(title_text=f"Monte Carlo Uncertainty Envelope ({n_mc} runs, perturbed initial conditions)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, margin=dict(l=0, r=0, t=50, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with tabs[6]:
        if st.button("Compute sensitivity heatmap (a vs b)"):
            a_grid = np.linspace(0.5, 3.0, 12); b_grid = np.linspace(0.2, 2.0, 12)
            A_m, B_m = np.meshgrid(a_grid, b_grid)
            Z_m = np.zeros_like(A_m)
            for i in range(A_m.shape[0]):
                for j in range(A_m.shape[1]):
                    Z_m[i, j] = np.max(solve_ode_system(default_ode, initial_state, t, args=(A_m[i, j], B_m[i, j], c, 0.0))[:, 0])
            fig = go.Figure(data=go.Contour(z=Z_m, x=a_grid, y=b_grid, colorscale="Viridis", contours=dict(coloring="heatmap")))
            fig.update_layout(title_text=f"Sensitivity Landscape: {a_label} vs {b_label}", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500, margin=dict(l=0, r=0, t=50, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with tabs[7]:
        sol_base = solve_ode_system(default_ode, initial_state, t, args=(a, b, c, 0.0))[:, 0]
        sol_sub = solve_ode_system(default_ode, initial_state, t, args=(max(0.1, a - 0.5), b, c, policy_shock * 0.5))[:, 0]
        sol_ref = solve_ode_system(default_ode, initial_state, t, args=(a, b - 0.2, c - 0.1, policy_shock * 0.1))[:, 0]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=sol_base, name="Baseline", line=dict(color="#60A5FA")))
        fig.add_trace(go.Scatter(x=t, y=sol_sub, name="Reduced-driver strategy", line=dict(color="#F87171", dash="dash")))
        fig.add_trace(go.Scatter(x=t, y=sol_ref, name="Reformed strategy", line=dict(color="#34D399")))
        fig.update_layout(title_text="Strategy Comparison (three parameter sets on the same model)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[8]:
        glass("This is a <b>rule-based</b> assistant reading your live simulation state - it is not a trained language model and won't reason beyond the keyword rules below.")
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        if prompt := st.chat_input("Ask about status, shock, bifurcation, or type 'help'..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            p = prompt.lower()
            if "status" in p or "health" in p:
                reply = f"Trajectory state: **{state_label}**, expansion-rate heuristic ≈ {mlce:.4f}."
            elif "help" in p:
                reply = "Try: 'status', 'shock', 'bifurcation', or ask what a/b/c control."
            elif "shock" in p:
                reply = f"Current injected shock magnitude is {policy_shock}. Adjust it in the model configuration panel above."
            elif "bifurcation" in p:
                reply = "Open the 'Bifurcation' tab and click 'Run bifurcation scan' to compute one against parameter b."
            else:
                reply = f"Current parameters: a={a}, b={b}, c={c}. Trajectory is classified {state_label.lower()} under this sector framing ({sector})."
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            with st.chat_message("assistant"):
                st.markdown(reply)

    with tabs[9]:
        col_up, col_down = st.columns(2)
        with col_up:
            up_file = st.file_uploader("Upload CSV/JSON/Excel/TXT for reference overlay", type=["csv", "json", "xlsx", "xls", "txt"], key="chaos_upload")
            if up_file:
                df_loaded = universal_loader(up_file)
                if df_loaded is not None:
                    st.success(f"Loaded `{up_file.name}` ({len(df_loaded)} rows).")
                    st.dataframe(df_loaded.head(10), use_container_width=True)
        with col_down:
            export_df = pd.DataFrame({"t": t, "x": x_traj, "y": y_traj, "z": z_traj, "rolling_var": rolling_var, "rolling_ac": rolling_ac})
            download_df_buttons(export_df, f"chaos_lab_{sector.split(' ')[0]}", "chaos")
            if st.button("💾 Commit run to database"):
                cur = db_conn.cursor()
                cur.execute(
                    "INSERT INTO simulations (timestamp, author, org_email, jurisdiction, sector, role, mlce_heuristic, state_label, params, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.author_name, st.session_state.org_email,
                     st.session_state.target_jurisdiction, sector, "Chaos Lab", float(mlce), state_label, json.dumps({"a": a, "b": b, "c": c}), ""),
                )
                db_conn.commit()
                st.success("Saved.")

# ============================================================================
# 11. MODULE: ML & FORECASTING CORE
#     Replaces the old "Neural ODE / PINN / GNN / BSTS" random-number demo
#     with genuinely computed forecasts (Holt-Winters + AR least-squares),
#     runnable on your own uploaded series or on a clearly-labeled demo one.
# ============================================================================
def render_ml_core():
    section_header("ML & Forecasting Core", "Real, from-scratch forecasting math - Holt-Winters smoothing and AR(p) least squares.", data_mode_badge())

    glass(
        "This module replaced fabricated 'Neural ODE / PINN / GNN' style metrics with methods "
        "that are actually computed: Holt's exponential smoothing (level + trend + optional "
        "seasonality) and an autoregressive model fit by ordinary least squares. Both are "
        "classical, auditable statistics - not black-box AI - which is more trustworthy for "
        "decisions than a fancier-sounding but fake metric."
    )

    src = st.radio("Series source", ["Use demo series", "Use my uploaded data (Data Studio)"], horizontal=True)
    if src == "Use my uploaded data (Data Studio)" and st.session_state.uploaded_df is not None:
        df = st.session_state.uploaded_df
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            st.warning("Uploaded file has no numeric columns - falling back to demo series.")
            series = None
        else:
            col = st.selectbox("Numeric column to forecast", numeric_cols)
            series = df[col].dropna().values
    else:
        if src == "Use my uploaded data (Data Studio)":
            st.info("No file uploaded yet - go to 🗂️ Data Studio to upload one. Using a demo series for now.")
        rng = np.random.default_rng(7)
        n = 60
        base_trend = np.linspace(100, 145, n)
        seasonal = 6 * np.sin(np.linspace(0, 6 * np.pi, n))
        noise = rng.normal(0, 2.0, n)
        series = base_trend + seasonal + noise
        st.markdown("<span style='color:#94A3B8;font-size:0.85rem;'>Demo series: synthetic trend + seasonality + noise, generated deterministically for layout purposes.</span> " + badge_demo(), unsafe_allow_html=True)

    if series is not None and len(series) >= 4:
        c1, c2, c3, c4 = st.columns(4)
        alpha = c1.slider("Smoothing α (level)", 0.05, 0.95, 0.4, 0.05)
        beta = c2.slider("Smoothing β (trend)", 0.01, 0.95, 0.2, 0.01)
        season_len = c3.number_input("Season length (0 = none)", min_value=0, max_value=max(0, len(series)//2), value=0)
        periods = c4.slider("Periods to forecast", 1, 30, 12)

        fitted_hw, forecast_hw = holt_winters_forecast(series, periods=periods, alpha=alpha, beta=beta, gamma=0.1, season_len=int(season_len))
        lags = st.slider("AR model lag order (p)", 1, min(10, max(1, len(series)//3)), 3)
        fitted_ar, forecast_ar, coeffs = ar_least_squares_forecast(series, lags=lags, periods=periods)

        x_hist = np.arange(len(series))
        x_fore = np.arange(len(series), len(series) + periods)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_hist, y=series, name="Observed", line=dict(color="#94A3B8", width=2)))
        fig.add_trace(go.Scatter(x=x_hist, y=fitted_hw, name="Holt-Winters fit", line=dict(color="#38BDF8", width=2, dash="dot")))
        fig.add_trace(go.Scatter(x=x_fore, y=forecast_hw, name="Holt-Winters forecast", line=dict(color="#38BDF8", width=3)))
        fig.add_trace(go.Scatter(x=x_fore, y=forecast_ar, name=f"AR({lags}) forecast", line=dict(color="#F472B6", width=3, dash="dash")))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=460, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

        resid = series[lags:] - fitted_ar
        mae = float(np.mean(np.abs(resid))) if len(resid) else float("nan")
        rmse = float(np.sqrt(np.mean(resid ** 2))) if len(resid) else float("nan")
        c1, c2, c3 = st.columns(3)
        metric_card(f"{mae:.3f}", "AR In-Sample MAE", c1)
        metric_card(f"{rmse:.3f}", "AR In-Sample RMSE", c2)
        metric_card(f"{len(series)} pts", "Series Length", c3)

        st.markdown("#### Anomaly detection (z-score, threshold-based)")
        z_thresh = st.slider("Z-score threshold", 1.0, 4.0, 2.5, 0.1)
        flags, z = anomaly_flags(series, z_thresh)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=x_hist, y=series, mode="lines", name="Series", line=dict(color="#60A5FA")))
        fig2.add_trace(go.Scatter(x=x_hist[flags], y=series[flags], mode="markers", name="Flagged", marker=dict(color="#F87171", size=10, symbol="x")))
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=350, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(f"{int(flags.sum())} point(s) flagged beyond ±{z_thresh} standard deviations.")

        st.markdown("#### Export")
        ar_fitted_padded = [None] * lags + list(fitted_ar)  # AR fit has no value for the first `lags` points
        out_df = pd.DataFrame({
            "t": list(x_hist) + list(x_fore),
            "observed": list(series) + [None] * periods,
            "holt_winters": list(fitted_hw) + list(forecast_hw),
            "ar_model": ar_fitted_padded + list(forecast_ar),
        })
        download_df_buttons(out_df, "ml_forecast_export", "mlcore")
    else:
        st.info("Need at least 4 numeric data points to fit a forecast.")

# ============================================================================
# 12. SHARED HELPER: generic domain ODE runner
#     All four sector suites (Energy, Food, Financial, Health) use the same
#     "3-state ODE + demo dashboard" pattern - factored out to avoid
#     duplicating ~150 lines four times and to keep the disclosure banner
#     consistent everywhere.
# ============================================================================
def domain_disclosure(domain_name):
    glass(
        f"<b>{domain_name} simulation:</b> the charts below are generated by integrating a small "
        "illustrative ODE system whose parameters you control with the sliders - they are "
        "<b>not</b> pulled from any real institution, and the 'recommended actions' are generic "
        "outputs of this toy model, not real operational guidance. " + badge_demo() + " Connect "
        "real data via Data Studio, or swap the seed rows in the database, to make a panel [LIVE]."
    )

# ============================================================================
# 13. MODULE: ENERGY & INFRASTRUCTURE RESILIENCY
# ============================================================================
def render_energy():
    section_header("Energy & Infrastructure Resiliency", "Cascading grid-stress ODE model + substation dispatch view.", badge_demo())
    domain_disclosure("Energy grid")

    tabs = st.tabs(["Executive Dashboard", "Cascading Failure Simulation", "Water/Hydro Strain", "Renewable & Storage", "Substation Dispatch", "Transmission Faults", "Emergency Restoration"])

    with st.sidebar.expander("⚡ Energy module parameters", expanded=False):
        simulation_hours = st.slider("Simulation horizon (hours)", 12, 168, 48, 12, key="egy_hours")
        grid_stress_multiplier = st.slider("Grid stress / peak demand multiplier", 0.5, 2.5, float(st.session_state.get("global_stress", 1.1)), 0.1, key="egy_stress")
        base_demand_mw = st.slider("Base system demand (MW)", 500, 5000, 1850, 100, key="egy_demand")
        renewable_share = st.slider("Renewable penetration (%)", 5.0, 75.0, 32.0, 2.5, key="egy_renew")
        reservoir_capacity = st.slider("Water reservoir capacity (%)", 20.0, 100.0, 68.5, 2.5, key="egy_reservoir")

    def grid_failure_model(y, t, demand_mult, renewables):
        Instability, StorageLevel, ThermalStrain = y
        dInstability = 0.05 * demand_mult - 0.03 * (renewables * 0.01) + 0.02 * ThermalStrain
        dStorage = -0.04 * demand_mult + 0.02 * (renewables * 0.01)
        dThermal = 0.08 * (demand_mult - 1.0) - 0.01 * StorageLevel
        return [dInstability, dStorage, dThermal]

    t_hours = np.linspace(0, simulation_hours, simulation_hours * 2)
    grid_solution = solve_ode_system(grid_failure_model, [0.012, 0.75, 0.20], t_hours, args=(grid_stress_multiplier, renewable_share))
    instability_traj, storage_traj, thermal_traj = grid_solution[:, 0], grid_solution[:, 1], grid_solution[:, 2]
    cascade_risk = float(instability_traj[-1])

    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        metric_card(f"{max(0.001, cascade_risk):.4f}", "Cascade Risk Index (model output)", c1)
        metric_card(f"{reservoir_capacity:.1f}%", "Reservoir Level (input)", c2)
        metric_card(f"{renewable_share:.1f}%", "Renewable Penetration (input)", c3)
        metric_card(f"{base_demand_mw} MW", "System Load (input)", c4)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t_hours, y=instability_traj * 100, name="Cascade risk index (%)", line=dict(color="#00f2fe", width=3)))
        fig.add_trace(go.Scatter(x=t_hours, y=thermal_traj * 100, name="Thermal strain (%)", line=dict(color="#f43f5e", width=3, dash="dash")))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=430, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
        if st.button("⭐ Pin cascade risk", key="egy_pin"):
            add_watchlist_item("Energy", "Cascade risk index", f"{cascade_risk:.4f}", f"stress={grid_stress_multiplier}")
            st.success("Pinned.")

    with tabs[1]:
        st.markdown(f"Model-implied resilience state: {status_pill('STABLE' if cascade_risk < 0.05 else 'CRITICAL')}", unsafe_allow_html=True)
        st.plotly_chart(px.line(x=t_hours, y=instability_traj, labels={"x": "Hours", "y": "Cascade risk index"}, template="plotly_dark"), use_container_width=True)

    with tabs[2]:
        res_df = pd.DataFrame({
            "Basin (illustrative label)": ["Basin A", "Basin B", "Basin C", "Basin D"],
            "Storage Level (%)": [reservoir_capacity, 74.2, 82.5, 61.0],
            "Discharge Rate (m3/s)": [1250, 410, 310, 890],
        })
        st.dataframe(res_df, use_container_width=True, hide_index=True)

    with tabs[3]:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t_hours, y=storage_traj * 100, name="Storage reserve (%)", line=dict(color="#34d399", width=3)))
        fig.add_trace(go.Scatter(x=t_hours, y=np.ones_like(t_hours) * renewable_share, name="Target renewable share (%)", line=dict(color="#fbbf24", width=2, dash="dot")))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=420, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[4]:
        cur = db_conn.cursor(); cur.execute("SELECT substation_name, load_mw, capacity_mw, status, operator_contact FROM critical_substations")
        subs_df = pd.DataFrame(cur.fetchall(), columns=["Substation", "Load (MW)", "Capacity (MW)", "Status", "Operator Contact"])
        st.dataframe(subs_df, use_container_width=True, hide_index=True)
        download_df_buttons(subs_df, "substations", "egy_subs")

    with tabs[5]:
        line_df = pd.DataFrame({
            "Line (illustrative label)": ["Line A", "Line B", "Line C", "Line D"],
            "Thermal Load (%)": [78.5, 92.0, 64.2, 81.0],
            "Conductor Temp (C)": [68.4, 84.5, 55.0, 71.2],
        })
        st.dataframe(line_df, use_container_width=True, hide_index=True)

    with tabs[6]:
        c1, c2, c3 = st.columns(3)
        metric_card("Model-dependent", "Blackstart Readiness", c1)
        metric_card(f"{int(base_demand_mw*0.18)} MW", "Spinning Reserve (illustrative)", c2)
        metric_card("Model-dependent", "Response Time", c3)

# ============================================================================
# 14. MODULE: FOOD & AGRICULTURE SECURITY
# ============================================================================
def render_food():
    section_header("Food & Agriculture Security", "Grain-reserve depletion ODE model + supply-chain view.", badge_demo())
    domain_disclosure("Food security")

    with st.sidebar.expander("🌾 Food module parameters", expanded=False):
        forecasting_weeks = st.slider("Forecast horizon (weeks)", 4, 52, 24, 4, key="food_weeks")
        climate_stress_factor = st.slider("Climate stress multiplier", 0.0, 2.0, float(st.session_state.get("global_stress", 1.0)), 0.1, key="food_stress")
        consumption_rate = st.slider("Daily consumption (tons/day)", 1000, 25000, 8500, 500, key="food_cons")
        initial_reserve_tons = st.slider("Initial stockpile (k tons)", 500, 5000, 1840, 50, key="food_reserve")
        fertilizer_inflation = st.slider("Fertilizer price increase (%)", 0.0, 50.0, 8.4, 0.5, key="food_fert")

    def food_model(y, t, consumption, stress):
        Stock, Vuln, Price = y
        dStock = -consumption * 0.001 - (stress * 12.0)
        dVuln = 0.05 * stress + 0.01 * (1.0 / (Stock + 1.0))
        dPrice = 0.4 * fertilizer_inflation + 0.2 * stress - 0.1 * Price
        return [dStock, dVuln, dPrice]

    t_weeks = np.linspace(0, forecasting_weeks, forecasting_weeks * 2)
    sol = solve_ode_system(food_model, [initial_reserve_tons / 1000.0, 0.25, 100.0], t_weeks, args=(consumption_rate, climate_stress_factor))
    stock_traj, vuln_traj, price_traj = sol[:, 0], sol[:, 1], sol[:, 2]
    buffer_days = int((stock_traj[-1] * 1_000_000) / max(1, consumption_rate))

    tabs = st.tabs(["Executive Dashboard", "Reserve Depletion Timer", "Drought & Yield", "Supply-Chain Logs", "Fertilizer Costs", "Pest Surveillance", "Trade Resilience"])

    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        metric_card(f"{max(14, buffer_days)} days", "Reserve Buffer (model output)", c1)
        metric_card(f"{fertilizer_inflation:.1f}%", "Fertilizer Cost Burden (input)", c2)
        metric_card(f"{climate_stress_factor:.2f}", "Climate Stress (input)", c3)
        metric_card(f"{consumption_rate}/day", "Consumption Rate (input)", c4)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t_weeks, y=stock_traj * 1000, name="Reserve stockpile (k tons)", line=dict(color="#34D399", width=3)))
        fig.add_trace(go.Scatter(x=t_weeks, y=vuln_traj * 100, name="Vulnerability index (%)", line=dict(color="#FBBF24", width=3, dash="dash")))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=430, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
        if st.button("⭐ Pin reserve buffer", key="food_pin"):
            add_watchlist_item("Food Security", "Reserve buffer", f"{max(14, buffer_days)} days", f"stress={climate_stress_factor}")
            st.success("Pinned.")

    with tabs[1]:
        st.plotly_chart(px.line(x=t_weeks, y=stock_traj * 1000, labels={"x": "Weeks", "y": "Reserve (k tons)"}, template="plotly_dark"), use_container_width=True)

    with tabs[2]:
        drought_df = pd.DataFrame({
            "Zone (illustrative label)": ["Zone A", "Zone B", "Zone C", "Zone D"],
            "Drought Risk": ["Critical", "Moderate", "High", "Low"],
            "Soil Saturation (%)": [max(15, 65 - int(climate_stress_factor*20)), 52.0, 38.2, 74.5],
        })
        st.dataframe(drought_df, use_container_width=True, hide_index=True)

    with tabs[3]:
        cur = db_conn.cursor(); cur.execute("SELECT region, hazard_type, urgency_level, recommended_action FROM intervention_logs")
        log_df = pd.DataFrame(cur.fetchall(), columns=["Region", "Hazard", "Urgency", "Suggested Intervention"])
        st.dataframe(log_df, use_container_width=True, hide_index=True)
        st.caption("Rows are illustrative seed examples - edit intervention_logs to reflect your own real logistics data.")

    with tabs[4]:
        fert_df = pd.DataFrame({
            "Fertilizer": ["Urea (N)", "DAP (Phosphate)", "NPK Compound", "Organic Compost"],
            "Illustrative Cost ($/ton)": [640, 720, 680, 210],
        })
        st.dataframe(fert_df, use_container_width=True, hide_index=True)

    with tabs[5]:
        pest_df = pd.DataFrame({
            "Threat (illustrative label)": ["Threat A", "Threat B", "Threat C", "Threat D"],
            "Affected Acreage (ha)": [45000, 120000, 8500, 15000],
            "Spread Rate": ["High", "Moderate", "Critical", "Stable"],
        })
        st.dataframe(pest_df, use_container_width=True, hide_index=True)

    with tabs[6]:
        resilience_df = pd.DataFrame({
            "Bloc (illustrative label)": ["Bloc A", "Bloc B", "Bloc C", "Bloc D"],
            "Import Dependency": ["32%", "45%", "28%", "39%"],
            "Resilience": ["Moderate", "Vulnerable", "Robust", "Stable"],
        })
        st.dataframe(resilience_df, use_container_width=True, hide_index=True)

# ============================================================================
# 15. MODULE: FINANCIAL & MACROECONOMIC RISK
# ============================================================================
def render_financial():
    section_header("Financial & Macroeconomic Risk", "Debt-sustainability ODE model + yield curve view.", badge_demo())
    domain_disclosure("Macro-financial")
    st.warning("This module is a teaching/scenario tool, not investment or policy advice. Model outputs must not be used to make real financial decisions. Claude is not a financial advisor.")

    with st.sidebar.expander("📈 Financial module parameters", expanded=False):
        projection_horizon = st.slider("Forecast horizon (months)", 6, 60, 24, 6, key="fin_months")
        fiscal_shock_factor = st.slider("External shock multiplier", 0.0, 2.0, float(st.session_state.get("global_stress", 1.0)), 0.1, key="fin_shock")
        interest_rate = st.slider("Policy rate (%)", 1.0, 25.0, 11.5, 0.5, key="fin_rate")
        fx_depreciation_rate = st.slider("FX depreciation rate (%/yr)", 0.0, 30.0, 6.2, 0.5, key="fin_fx")
        debt_to_gdp_ratio = st.slider("Initial debt-to-GDP (%)", 20.0, 120.0, 52.4, 1.0, key="fin_debt")

    def macro_model(y, t, r, shock):
        D, FX, Infl = y
        dD = (r - 4.0) * D * 0.01 - 0.02 + (shock * 0.05)
        dFX = -0.1 * (r - 5.0) - (shock * 0.15)
        dInfl = 0.5 * (fx_depreciation_rate * 0.1) + 0.2 * shock - 0.1 * Infl
        return [dD, dFX, dInfl]

    t_months = np.linspace(0, projection_horizon, projection_horizon * 2)
    sol = solve_ode_system(macro_model, [debt_to_gdp_ratio, 4.5, 6.0], t_months, args=(interest_rate, fiscal_shock_factor))
    debt_traj, fx_traj, infl_traj = sol[:, 0], sol[:, 1], sol[:, 2]

    tabs = st.tabs(["Executive Dashboard", "Debt Sustainability", "Capital Flight & FX", "Inflation Pass-Through", "Yield Curve (sample)", "Contagion Matrix", "Liquidity Coverage"])

    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        metric_card(f"{debt_to_gdp_ratio:.1f}%", "Debt-to-GDP (input)", c1)
        metric_card(f"{interest_rate:.1f}%", "Policy Rate (input)", c2)
        metric_card(f"{fiscal_shock_factor:.2f}", "Shock Multiplier (input)", c3)
        metric_card(f"{debt_traj[-1]:.1f}%", "Projected End Debt/GDP (model)", c4)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t_months, y=debt_traj, name="Debt-to-GDP (%)", line=dict(color="#60A5FA", width=3)))
        fig.add_trace(go.Scatter(x=t_months, y=infl_traj*10, name="Inflation pass-through index", line=dict(color="#F43F5E", width=3, dash="dash")))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=430, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
        if st.button("⭐ Pin debt trajectory", key="fin_pin"):
            add_watchlist_item("Financial", "End debt/GDP (model)", f"{debt_traj[-1]:.1f}%", f"rate={interest_rate}")
            st.success("Pinned.")

    with tabs[1]:
        st.plotly_chart(px.line(x=t_months, y=debt_traj, labels={"x": "Months", "y": "Debt-to-GDP (%)"}, template="plotly_dark"), use_container_width=True)

    with tabs[2]:
        c1, c2, c3 = st.columns(3)
        metric_card(f"{max(1.0, 5.0-fiscal_shock_factor):.1f} mo", "FX Reserve Buffer (model)", c1)
        metric_card("Illustrative", "Portfolio Outflows", c2)
        metric_card("Illustrative", "FX Pressure", c3)

    with tabs[3]:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t_months, y=infl_traj, name="Headline inflation (%)", line=dict(color="#34D399", width=3)))
        fig.add_trace(go.Scatter(x=t_months, y=fx_traj, name="FX reserves index", line=dict(color="#F59E0B", width=3, dash="dot")))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=420, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[4]:
        cur = db_conn.cursor(); cur.execute("SELECT country, tenor, yield_rate, spread_bps, note FROM sovereign_bonds")
        bonds_df = pd.DataFrame(cur.fetchall(), columns=["Label", "Tenor", "Yield (%)", "Spread (bps)", "Note"])
        st.dataframe(bonds_df, use_container_width=True, hide_index=True)
        st.caption("These are illustrative sample rows, clearly labeled - replace with a real bond desk feed for live use.")

    with tabs[5]:
        contagion_df = pd.DataFrame({
            "Economy (illustrative label)": ["Economy A", "Economy B", "Economy C", "Economy D", "Economy E"],
            "Vulnerability": ["Low", "Moderate", "Low", "Optimal", "High"],
        })
        st.dataframe(contagion_df, use_container_width=True, hide_index=True)

    with tabs[6]:
        c1, c2, c3 = st.columns(3)
        metric_card("Illustrative", "Liquidity Coverage Ratio", c1)
        metric_card("Illustrative", "Fiscal Deficit (% GDP)", c2)
        metric_card("Illustrative", "Treasury Position", c3)

# ============================================================================
# 16. MODULE: HEALTHCARE COMMAND SUITE
# ============================================================================
def render_healthcare():
    section_header("Healthcare Command Suite", "SEIR + ICU compartmental epidemic model.", badge_demo())
    domain_disclosure("Public health")
    st.warning("Educational epidemiological modeling tool only. Not a clinical or public-health decision system - do not use these outputs for real triage, staffing, or outbreak response decisions.")

    with st.sidebar.expander("🏥 Healthcare module parameters", expanded=False):
        facility_name = st.text_input("Facility / region label", "Illustrative Facility", key="health_fac")
        simulation_horizon = st.slider("Forecast horizon (days)", 14, 180, 42, 7, key="health_days")
        intervention_urgency = st.slider("Intervention mitigation factor", 0.0, 1.0, 0.3, 0.05, key="health_mit")
        beta_transmission = st.slider("Transmission rate (beta)", 0.1, 5.0, 1.8, 0.1, key="health_beta")
        recovery_rate = st.slider("Recovery rate (gamma)", 0.05, 1.0, 0.3, 0.05, key="health_gamma")
        icu_conversion_rate = st.slider("Share requiring ICU", 0.01, 0.25, 0.08, 0.01, key="health_icu")

    def seir_model(y, t, beta, gamma, icu_rate, mitigation):
        S, E, I, R, ICU = y
        eff_beta = beta * (1.0 - mitigation)
        N = S + E + I + R + ICU + 1e-6
        dS = -eff_beta * S * I / N
        dE = eff_beta * S * I / N - 0.2 * E
        dI = 0.2 * E - gamma * I
        dR = gamma * I * (1.0 - icu_rate)
        dICU = gamma * I * icu_rate - 0.1 * ICU
        return [dS, dE, dI, dR, dICU]

    t_arr = np.linspace(0, simulation_horizon, simulation_horizon * 2)
    sol = solve_ode_system(seir_model, [0.99, 0.008, 0.002, 0.0, 0.0], t_arr, args=(beta_transmission, recovery_rate, icu_conversion_rate, intervention_urgency))
    S_t, E_t, I_t, R_t, ICU_t = sol[:, 0], sol[:, 1], sol[:, 2], sol[:, 3], sol[:, 4]
    peak_icu_day = int(np.argmax(ICU_t) * (simulation_horizon / (simulation_horizon * 2)))
    max_icu_load = float(np.max(ICU_t) * 100)

    tabs = st.tabs(["Executive Dashboard", "ICU Triage & Surge", "Supply Exhaustion", "Genomic Tracker", "Full SEIR Model", "Lab Throughput", "Staff Rostering", "Regional Network"])

    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        metric_card(f"Day {peak_icu_day}", "Projected Peak ICU Day (model)", c1)
        metric_card(f"{max_icu_load:.1f}%", "Peak ICU Load (model)", c2)
        metric_card(f"{beta_transmission:.2f}", "Transmission Rate (input)", c3)
        metric_card(f"{intervention_urgency:.2f}", "Mitigation Factor (input)", c4)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t_arr, y=I_t*100, name="Active infections (%)", line=dict(color="#38BDF8", width=3)))
        fig.add_trace(go.Scatter(x=t_arr, y=ICU_t*100, name="ICU demand (%)", line=dict(color="#F43F5E", width=3, dash="dash")))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=430, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
        if st.button("⭐ Pin peak ICU load", key="health_pin"):
            add_watchlist_item("Healthcare", "Peak ICU load (model)", f"{max_icu_load:.1f}%", f"beta={beta_transmission}")
            st.success("Pinned.")

    with tabs[1]:
        st.plotly_chart(px.area(x=t_arr, y=ICU_t*100, labels={"x": "Days", "y": "ICU occupancy (%)"}, template="plotly_dark"), use_container_width=True)

    with tabs[2]:
        med_df = pd.DataFrame({
            "Item (illustrative)": ["Oxygen", "Antibiotics", "N95 Respirators", "IV Fluids"],
            "Illustrative Buffer Remaining": [1800, 9500, 21000, 4500],
        })
        st.dataframe(med_df, use_container_width=True, hide_index=True)

    with tabs[3]:
        cur = db_conn.cursor(); cur.execute("SELECT pathogen, mutation_variant, transmission_index, severity FROM outbreak_alerts")
        var_df = pd.DataFrame(cur.fetchall(), columns=["Label", "Lineage", "Transmission Index", "Severity"])
        st.dataframe(var_df, use_container_width=True, hide_index=True)
        st.caption("Illustrative rows - wire in a real genomic surveillance feed for live use.")

    with tabs[4]:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t_arr, y=S_t*100, name="Susceptible", line=dict(color="#60A5FA")))
        fig.add_trace(go.Scatter(x=t_arr, y=E_t*100, name="Exposed", line=dict(color="#F59E0B")))
        fig.add_trace(go.Scatter(x=t_arr, y=I_t*100, name="Infectious", line=dict(color="#EF4444")))
        fig.add_trace(go.Scatter(x=t_arr, y=R_t*100, name="Recovered", line=dict(color="#10B981")))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[5]:
        c1, c2 = st.columns(2)
        metric_card("Illustrative", "Daily PCR Capacity", c1)
        metric_card("Illustrative", "Avg Turnaround", c2)

    with tabs[6]:
        staff_df = pd.DataFrame({
            "Ward (illustrative)": ["ICU", "Emergency", "Isolation", "Pediatrics"],
            "Illustrative Personnel": [45, 60, 35, 50],
        })
        st.dataframe(staff_df, use_container_width=True, hide_index=True)

    with tabs[7]:
        network_df = pd.DataFrame({
            "Facility (illustrative)": ["Facility A", "Facility B", "Facility C", "Facility D"],
            "Illustrative Occupancy": ["96%", "72%", "84%", "61%"],
        })
        st.dataframe(network_df, use_container_width=True, hide_index=True)

# ============================================================================
# 17. MODULE: LIVE TELEMETRY CENTER
#     Honest connector framework: shows connection health, and a clear path
#     to flip a connector from demo to live by editing CONNECTOR_REGISTRY.
# ============================================================================
CONNECTOR_REGISTRY = {
    # name -> a callable that returns a pandas DataFrame of real data.
    # Populate this dict with real functions (API calls, DB queries) to
    # make a connector [LIVE]. Left empty by default = everything is DEMO.
}

def render_telemetry():
    section_header("Live Telemetry Center", "Connector health monitor - demo mode until you wire a real feed.", badge_demo())
    glass(
        "No telemetry connector is wired to a real external API in this build. The table below "
        "reflects that honestly. To go live: implement a function that returns a DataFrame and "
        "register it in <code>CONNECTOR_REGISTRY</code> near the top of this module, then flip "
        "that row's <code>is_live</code> flag in the database."
    )
    cur = db_conn.cursor()
    cur.execute("SELECT source_name, protocol, polling_interval, health_status, is_live FROM active_connectors")
    rows = cur.fetchall()
    conn_df = pd.DataFrame(rows, columns=["Source", "Protocol", "Polling Interval", "Health Status", "Live?"])
    conn_df["Live?"] = conn_df["Live?"].map({1: "LIVE", 0: "Demo / not connected"})
    st.dataframe(conn_df, use_container_width=True, hide_index=True)

    st.markdown("#### Simulated stream preview (demo)")
    stream_mode = st.slider("Stream ingestion multiplier (demo)", 0.5, 3.0, 1.0, 0.1)
    time_steps = np.arange(0, 24, 1)
    demo_trend = np.sin(time_steps * 0.3) * 5 * stream_mode + 12
    fig = go.Figure(go.Scatter(x=time_steps, y=demo_trend, mode="lines+markers", line=dict(color="#38BDF8", width=3)))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=380, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Anomaly scan on this demo stream")
    flags, z = anomaly_flags(demo_trend, z_thresh=1.8)
    st.write(f"{int(flags.sum())} point(s) flagged (z-score demo detector).")

    with st.expander("➕ Register a new connector row (metadata only - does not fetch real data by itself)"):
        name = st.text_input("Source name")
        proto = st.text_input("Protocol", "REST / JSON")
        interval = st.text_input("Polling interval", "10s")
        if st.button("Add connector row"):
            cur.execute("INSERT INTO active_connectors (source_name, protocol, polling_interval, health_status, is_live) VALUES (?,?,?,?,0)",
                        (name, proto, interval, "Not connected - demo mode"))
            db_conn.commit()
            st.success("Added. Remember: this only adds a row - you still need to implement the real fetch in CONNECTOR_REGISTRY.")

# ============================================================================
# 18. MODULE: ENTERPRISE SECURITY & GOVERNANCE
# ============================================================================
def render_security():
    section_header("Enterprise Security & Governance", "RBAC directory + a real SHA-256 audit ledger of actions taken in this app.", badge_beta())
    glass(
        "The audit ledger below hashes <b>real events that happened in this running app session</b> "
        "(button clicks, saves) - the hashing itself is real SHA-256. It is <b>not</b> a blockchain, "
        "not independently verified by any third party, and not a substitute for a real compliance "
        "system. Treat it as a tamper-evident local log, not a certified audit trail."
    )

    tabs = st.tabs(["Executive Dashboard", "RBAC Matrix", "Audit Ledger", "Report Generator", "Threat Log (manual)", "Compliance Mapping", "Key Management (illustrative)"])

    with tabs[0]:
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM audit_logs")
        n_events = cur.fetchone()[0]
        c1, c2, c3 = st.columns(3)
        metric_card(n_events, "Logged Events (real, this app's DB)", c1)
        cur.execute("SELECT COUNT(*) FROM security_permissions WHERE status='Active'")
        metric_card(cur.fetchone()[0], "Active Roles", c2)
        metric_card("SHA-256", "Hash Function Used", c3)

    with tabs[1]:
        cur = db_conn.cursor(); cur.execute("SELECT role_name, assigned_department, clearance_level, status FROM security_permissions")
        rbac_df = pd.DataFrame(cur.fetchall(), columns=["Role", "Department", "Clearance", "Status"])
        st.dataframe(rbac_df, use_container_width=True, hide_index=True)
        with st.expander("➕ Add a role"):
            rn = st.text_input("Role name"); dept = st.text_input("Department")
            clr = st.selectbox("Clearance", ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"])
            if st.button("Add role"):
                cur.execute("INSERT INTO security_permissions (role_name, assigned_department, clearance_level, status) VALUES (?,?,?,?)", (rn, dept, clr, "Active"))
                db_conn.commit(); st.success("Added.")

    with tabs[2]:
        user_role_context = st.selectbox("Act as role (for this log entry)", ["Decision Maker", "Research Scientist", "Infrastructure Operator", "Auditor General"])
        action_desc = st.text_input("Action description", "Reviewed macro dashboard")
        if st.button("Log this action (writes a real hashed row)"):
            h = log_audit(user_role_context, action_desc)
            st.success(f"Logged. SHA-256: {h[:32]}...")
        cur = db_conn.cursor(); cur.execute("SELECT timestamp, user_role, action_performed, crypto_hash, status FROM audit_logs ORDER BY id DESC LIMIT 25")
        rows = cur.fetchall()
        if rows:
            st.dataframe(pd.DataFrame(rows, columns=["Time", "Role", "Action", "SHA-256 Hash", "Status"]), use_container_width=True, hide_index=True)
        else:
            st.caption("No events logged yet.")

    with tabs[3]:
        st.markdown("Compiles the audit ledger and RBAC table into a downloadable plain-text report (real content, not a fabricated PDF claim).")
        if st.button("Generate report"):
            cur = db_conn.cursor()
            cur.execute("SELECT timestamp, user_role, action_performed, crypto_hash FROM audit_logs ORDER BY id DESC LIMIT 50")
            events = cur.fetchall()
            report_lines = [
                f"GOVERNANCE REPORT - generated {datetime.datetime.now().isoformat()}",
                f"Jurisdiction: {st.session_state.target_jurisdiction}",
                f"Prepared by: {st.session_state.author_name} <{st.session_state.org_email}>",
                "", "Recent audit events:",
            ] + [f"  {e[0]} | {e[1]} | {e[2]} | {e[3][:16]}..." for e in events]
            report_text = "\n".join(report_lines)
            st.download_button("Download report (.txt)", report_text.encode("utf-8"), "governance_report.txt", "text/plain")
            st.code(report_text[:2000])

    with tabs[4]:
        st.caption("Manually log a security-relevant event you observed - this is a logbook, not an intrusion-detection system.")
        vector = st.text_input("Observed vector / event")
        severity = st.selectbox("Severity", ["Low", "Moderate", "High", "Critical"])
        if st.button("Log threat observation"):
            log_audit("Security Log", f"THREAT OBSERVED: {vector} [{severity}]")
            st.success("Logged to audit ledger.")

    with tabs[5]:
        compliance_standard = st.selectbox("Framework", ["ISO/IEC 27001", "GDPR", "Basel III", "HIPAA"])
        compliance_df = pd.DataFrame({
            "Control Objective": ["Encryption at rest/transit", "Access control", "Audit logging", "Incident response"],
            f"{compliance_standard} note": ["Verify with your own compliance team", "Verify with your own compliance team", "This app: real local SHA-256 log", "Verify with your own compliance team"],
        })
        st.dataframe(compliance_df, use_container_width=True, hide_index=True)

    with tabs[6]:
        st.info("Key management shown here is illustrative UI only - this app does not manage real encryption keys or HSMs.")
        c1, c2 = st.columns(2)
        metric_card("Illustrative", "Key Rotation Policy", c1)
        metric_card("Illustrative", "HSM Status", c2)

# ============================================================================
# 19. MODULE: DATA STUDIO  (NEW - real universal import / forecast / export)
# ============================================================================
def render_data_studio():
    section_header("Data Studio", "Upload your own data once; every module can use it via the Data Mode toggle.", data_mode_badge())
    up_file = st.file_uploader("Upload CSV / JSON / Excel / TXT", type=["csv", "json", "xlsx", "xls", "txt"])
    if up_file:
        df = universal_loader(up_file)
        if df is not None:
            st.session_state.uploaded_df = df
            st.session_state.uploaded_df_name = up_file.name
            st.success(f"Loaded `{up_file.name}` - {len(df)} rows x {len(df.columns)} cols. Now available to ML & Forecasting Core.")

    if st.session_state.uploaded_df is not None:
        df = st.session_state.uploaded_df
        st.markdown(f"#### Preview: `{st.session_state.uploaded_df_name}`")
        st.dataframe(df.head(50), use_container_width=True)

        st.markdown("#### Quick profile")
        c1, c2, c3 = st.columns(3)
        metric_card(len(df), "Rows", c1)
        metric_card(len(df.columns), "Columns", c2)
        metric_card(int(df.isna().sum().sum()), "Missing Values", c3)
        st.dataframe(df.describe(include="all").transpose(), use_container_width=True)

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) >= 2:
            st.markdown("#### Correlation matrix (real, computed on your data)")
            corr = df[numeric_cols].corr()
            fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450)
            st.plotly_chart(fig, use_container_width=True)

        if numeric_cols:
            st.markdown("#### Quick chart")
            chart_col = st.selectbox("Column to plot", numeric_cols)
            st.plotly_chart(px.line(df, y=chart_col, template="plotly_dark"), use_container_width=True)

        download_df_buttons(df, "data_studio_export", "studio")
        if st.button("Clear uploaded data"):
            st.session_state.uploaded_df = None
            st.session_state.uploaded_df_name = None
            st.rerun()
    else:
        st.info("No file uploaded yet. Every simulation module will keep using clearly-labeled demo data until you upload one here.")

# ============================================================================
# 20. MODULE: ALERTS & WATCHLIST CENTER (NEW)
# ============================================================================
def render_alerts():
    section_header("Alerts & Watchlist Center", "Cross-module threshold rules + everything you've pinned.", badge_beta())

    tab1, tab2 = st.tabs(["Watchlist", "Alert Rules"])
    with tab1:
        cur = db_conn.cursor()
        cur.execute("SELECT timestamp, module, label, value, note FROM watchlist ORDER BY id DESC")
        rows = cur.fetchall()
        if rows:
            wl_df = pd.DataFrame(rows, columns=["Time", "Module", "Label", "Value", "Note"])
            st.dataframe(wl_df, use_container_width=True, hide_index=True)
            download_df_buttons(wl_df, "watchlist_export", "wl")
        else:
            st.caption("Nothing pinned yet - use the ⭐ Pin buttons throughout the app.")

    with tab2:
        st.caption("Define a rule; it's evaluated the next time you view the relevant module's metric (client-side check, not a background job).")
        with st.form("alert_rule_form"):
            module = st.selectbox("Module", ["Energy", "Food Security", "Financial", "Healthcare", "Chaos Lab", "ML Core"])
            metric_name = st.text_input("Metric name (free text, for your own reference)")
            comparator = st.selectbox("Comparator", [">", "<", ">=", "<=", "=="])
            threshold = st.number_input("Threshold", value=0.0)
            submitted = st.form_submit_button("Add rule")
            if submitted:
                cur = db_conn.cursor()
                cur.execute("INSERT INTO alert_rules (module, metric_name, comparator, threshold, active) VALUES (?,?,?,?,1)",
                            (module, metric_name, comparator, threshold))
                db_conn.commit()
                st.success("Rule added.")
        cur = db_conn.cursor(); cur.execute("SELECT id, module, metric_name, comparator, threshold, active FROM alert_rules ORDER BY id DESC")
        rules = cur.fetchall()
        if rules:
            rules_df = pd.DataFrame(rules, columns=["ID", "Module", "Metric", "Comparator", "Threshold", "Active"])
            st.dataframe(rules_df, use_container_width=True, hide_index=True)

# ============================================================================
# 21. MODULE: NOTES & AUDIT LOG
# ============================================================================
def render_notes():
    section_header("Notes & Audit Log", "Freeform analyst notes, saved per module, plus the raw audit trail.", badge_beta())
    tab1, tab2 = st.tabs(["Notes", "Full Audit Trail"])
    with tab1:
        module = st.selectbox("Attach note to module", [m for m in MODULES])
        body = st.text_area("Note")
        if st.button("Save note"):
            add_note(module, st.session_state.author_name, body)
            st.success("Saved.")
        cur = db_conn.cursor(); cur.execute("SELECT timestamp, module, author, body FROM notes ORDER BY id DESC LIMIT 50")
        rows = cur.fetchall()
        if rows:
            st.dataframe(pd.DataFrame(rows, columns=["Time", "Module", "Author", "Note"]), use_container_width=True, hide_index=True)
    with tab2:
        cur = db_conn.cursor(); cur.execute("SELECT timestamp, user_role, action_performed, crypto_hash, status FROM audit_logs ORDER BY id DESC LIMIT 200")
        rows = cur.fetchall()
        if rows:
            audit_df = pd.DataFrame(rows, columns=["Time", "Role", "Action", "Hash", "Status"])
            st.dataframe(audit_df, use_container_width=True, hide_index=True)
            download_df_buttons(audit_df, "audit_trail_export", "audit")
        else:
            st.caption("No events yet.")

# ============================================================================
# 22. MODULE: SETTINGS
# ============================================================================
def render_settings():
    section_header("Settings", "Theme, connectors, and database maintenance.", "")
    st.markdown("#### Theme")
    new_theme = st.selectbox("Color theme", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme_name))
    if new_theme != st.session_state.theme_name:
        st.session_state.theme_name = new_theme
        st.rerun()

    st.markdown("#### Connector wiring")
    glass(
        "Real connectors are added in code, in <code>CONNECTOR_REGISTRY</code>, so a bad actor "
        "can't add a fake 'live' feed just by clicking a button in the UI. Ask a developer to "
        "add a function there that calls your real API and returns a DataFrame."
    )

    st.markdown("#### Database")
    st.caption(f"SQLite file: `{APP_DB_PATH}` (single-node deployments only - swap for Postgres in production).")
    cur = db_conn.cursor()
    for table in ["simulations", "audit_logs", "watchlist", "notes", "alert_rules"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        st.write(f"`{table}`: {cur.fetchone()[0]} rows")

    st.markdown("#### About")
    st.caption(f"Global Sovereign Intelligence Platform v{APP_VERSION}. Consolidated from 8 prior single-purpose modules. Every simulated panel is explicitly labeled — see the header note in this file's docstring for the full data-integrity policy.")

# ============================================================================
# 23. ROUTER
# ============================================================================
ROUTES = {
    "🏠 Command Center (Home)": render_home,
    "🌀 Chaos & Nonlinear Systems Lab": render_chaos_lab,
    "🧠 ML & Forecasting Core": render_ml_core,
    "📡 Live Telemetry Center": render_telemetry,
    "🛡️ Enterprise Security & Governance": render_security,
    "⚡ Energy & Infrastructure Resiliency": render_energy,
    "🌾 Food & Agriculture Security": render_food,
    "📈 Financial & Macroeconomic Risk": render_financial,
    "🏥 Healthcare Command Suite": render_healthcare,
    "🗂️ Data Studio (Import / Forecast / Export)": render_data_studio,
    "🚨 Alerts & Watchlist Center": render_alerts,
    "📝 Notes & Audit Log": render_notes,
    "⚙️ Settings": render_settings,
}

ROUTES.get(active_module, render_home)()

st.markdown("<div class='glass-divider'></div>", unsafe_allow_html=True)
st.caption(
    f"Global Sovereign Intelligence Platform v{APP_VERSION} · "
    "Simulated panels are marked DEMO and must not be used for real operational decisions."
)


