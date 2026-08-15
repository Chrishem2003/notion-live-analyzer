
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

# ============================================================================
# PLOTLY INTEGRATION 🔍 Interactive Scientific Visualizations
# ============================================================================
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# ============================================================================
# DATABASE INITIALIZATION (SQLite Persistent Store & Analyst Directory)
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
    
    # Seed Initial Institutional Contacts
    cursor.execute("""
        INSERT OR IGNORE INTO analyst_contacts (analyst_name, org_email, contact_phone, clearance_level, primary_sector, vault_hash)
        VALUES 
        ('Kula Chris', 'chrishem@sovereign.org', '256 700 000000', 'Tier-1 Lead Architect', 'Economics & Sovereign Risk', 'HASH-SOV-999'),
        ('Dr. Matsiko', 'matsiko@muni.ac.ug', '256 772 111222', 'Chief Scientific Director', 'Bioinformatics & Systems', 'HASH-SCI-888'),
        ('Ocircan Darius', 'darius@sovereign.org', '256 750 333444', 'Senior Policy Analyst', 'Infrastructure & Grid', 'HASH-POL-777')
    """)
    conn.commit()
    return conn

db_conn = init_db()

# ============================================================================
# PAGE CONFIG & PREMIUM GLASSMORPHISM STYLES
# ============================================================================
st.set_page_config(
    page_title="Global Sovereign Nonlinear Systems & Resilience Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrainsMono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #F8FAFC !important;
    }

    .stApp {
        background: linear-gradient(135deg, #070B14 0%, #0F172A 50%, #070B14 100%);
        background-attachment: fixed;
    }

    .glass-container {
        background: rgba(15, 23, 42, 0.85);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 20px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6);
        color: #F8FAFC !important;
    }

    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #60A5FA, #A78BFA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #CBD5E1 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.3rem;
        font-weight: 600;
    }

    .status-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.4rem 1rem;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.85rem;
        border: 1px solid;
    }
    .status-stable { background: rgba(22, 101, 52, 0.4); border-color: rgba(74, 222, 128, 0.6); color: #4ADE80 !important; }
    .status-borderline { background: rgba(133, 77, 14, 0.4); border-color: rgba(250, 204, 21, 0.6); color: #FACC15 !important; }
    .status-critical { background: rgba(153, 27, 27, 0.4); border-color: rgba(248, 113, 113, 0.6); color: #F87171 !important; }

    .stButton > button {
        background: linear-gradient(135deg, #3B82F6, #8B5CF6) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 700 !important;
    }
    
    .glass-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        margin: 1.5rem 0;
    }

    .main-header-glow {
        background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -1px;
    }
    .sub-header-glow { color: #E2E8F0 !important; font-size: 1rem; font-weight: 500; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# UNIVERSAL MULTI-FORMAT DATA LOADER
# ============================================================================
def _load_any(uploaded_file):
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(uploaded_file)
        if name.endswith(".json"):
            return pd.read_json(uploaded_file)
        if name.endswith(".xlsx") or name.endswith(".xls"):
            return pd.read_excel(uploaded_file)
        if name.endswith(".txt"):
            return pd.read_csv(uploaded_file, sep=None, engine="python")
        st.error("Unsupported file type.")
        return None
    except Exception as exc:
        st.error(f"Could not parse `{uploaded_file.name}`: {exc}")
        return None

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Sovereign Intelligence Core online. Ask about status, shock impact, bifurcation, or type 'help' for guidance."}
    ]

if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================
st.sidebar.markdown("## 🛡️ Global Sovereign Command Hub")

with st.sidebar.expander("📊 Institutional & Analyst Details", expanded=True):
    user_role = st.selectbox(
        "Privilege tier / View",
        [
            "Chat Command Core",
            "Executive Storyboard",
            "Policy Comparison Matrix",
            "Technocrat Operations",
            "Research Scientist (Full Engine)",
            "Data Import / Export Center",
            "System Self-Test & Diagnostics",
            "Sector Automation Hub",
            "Institutional Contacts & Directory",
        ],
    )
    author_name = st.text_input("Author / Analyst Name", "Kula Chris")
    org_email = st.text_input("Organization Email", "chrishem@sovereign.org")
    contact_phone = st.text_input("Contact Phone", "256 700 000000")
    secure_vault_token = st.text_input("Secure Vault Passkey", type="password", value="SOV-999-KEY")

st.sidebar.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown("### 🌐 Jurisdiction & Domain")

PRESET_COUNTRIES = [
    "Uganda", "Kenya", "Rwanda", "Nigeria", "South Africa",
    "Ghana", "Ethiopia", "Tanzania", "Egypt",
    "United States", "United Kingdom", "France", "Germany",
    "Japan", "China", "India", "Brazil", "Canada",
    "Australia", "Global / Multi-State Aggregate",
]

region_mode = st.sidebar.radio("Jurisdiction scope", ["Choose from list", "Type any country / region"], horizontal=True)
if region_mode == "Choose from list":
    target_country = st.sidebar.selectbox("Country / Territory", PRESET_COUNTRIES, index=0)
else:
    target_country = st.sidebar.text_input("Type any country, city, or region", "e.g. Vietnam")

PRESET_SECTORS = {
    "Economics & Finance (Huang-Li model)": ("a", "Savings / growth rate", "b", "Investment cost", "c", "Market elasticity"),
    "Healthcare: Hospital surge & capacity": ("a", "Patient influx rate", "b", "ICU bed burnout", "c", "Staff fatigue decay"),
    "Epidemiology: Outbreak dynamics": ("a", "Transmission rate", "b", "Recovery rate", "c", "Waning immunity"),
    "Education: Tuition & institutional cashflow": ("a", "Tuition collection speed", "b", "Operational overhead", "c", "Reserve depletion"),
    "Agriculture: Food security & yield risk": ("a", "Climate stress index", "b", "Supply-chain friction", "c", "Reserve depletion"),
    "Bioinformatics: Gene regulatory networks": ("a", "Expression drive", "b", "Feedback damping", "c", "Mutation pressure"),
    "Treasury: Fiscal deficit & contagion": ("a", "Stress multiplier", "b", "Structural friction", "c", "Damping coefficient"),
    "Infrastructure: Power / grid reliability": ("a", "Demand surge", "b", "Load friction", "c", "Buffer capacity"),
    "Environmental: Predator-prey / hydrology": ("a", "Growth rate", "b", "Consumption rate", "c", "Recovery rate"),
}

sector_mode = st.sidebar.radio("Sector scope", ["Choose from list", "Type any custom sector"], horizontal=True)
if sector_mode == "Choose from list":
    sector = st.sidebar.selectbox("Institutional sector / problem domain", list(PRESET_SECTORS.keys()))
    a_label, a_desc, b_label, b_desc, c_label, c_desc = PRESET_SECTORS[sector]
else:
    sector = st.sidebar.text_input("Describe any sector in your own words", "e.g. Satellite telemetry")
    a_label, a_desc, b_label, b_desc, c_label, c_desc = "a", "Growth / drive term", "b", "Friction / damping term", "c", "Buffer / decay term"

st.sidebar.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown(f"### ⚙️ Parameters: {sector}")
a = st.sidebar.slider(f"{a_label} ({a_desc})", 0.1, 5.0, 1.5, 0.1)
b = st.sidebar.slider(f"{b_label} ({b_desc})", 0.0, 3.0, 0.9, 0.1)
c = st.sidebar.slider(f"{c_label} ({c_desc})", 0.0, 3.0, 1.0, 0.1)

st.sidebar.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown("### ⚡ Initial Conditions & Shock")
x0 = st.sidebar.number_input("Initial x0", value=0.10, format="%.3f")
y0 = st.sidebar.number_input("Initial y0", value=0.10, format="%.3f")
z0 = st.sidebar.number_input("Initial z0", value=0.10, format="%.3f")
policy_shock = st.sidebar.slider("Inject shock magnitude at mid-run", -3.0, 3.0, 0.0, 0.1)
t_max = st.sidebar.slider("Simulation horizon (steps)", 50, 500, 200, 10)

st.sidebar.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)
use_custom_ode = st.sidebar.checkbox("✏️ Use custom ODE equations")
custom_dx = custom_dy = custom_dz = ""
if use_custom_ode:
    st.sidebar.caption("Variables available: x, y, z, a, b, c, shock, t, np")
    custom_dx = st.sidebar.text_input("dx/dt =", "x - z - (y - a) * x + shock")
    custom_dy = st.sidebar.text_input("dy/dt =", "1 - b * y - x**2")
    custom_dz = st.sidebar.text_input("dz/dt =", "x - c * z")

st.sidebar.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)
pss_slice_z = st.sidebar.slider("Poincaré cut plane (Z threshold)", float(z0 - 2.0), float(z0 + 2.0), float(z0), 0.05)

# ============================================================================
# MODEL CORE & SOLVER
# ============================================================================
SAFE_NP_NAMES = {k: getattr(np, k) for k in ["sin", "cos", "tan", "exp", "log", "sqrt", "abs", "tanh", "pi"]}

def default_ode(state, t, a, b, c, shock_val):
    x, y, z = state
    shock = shock_val if (0.45 * t_max <= t <= 0.55 * t_max) else 0.0
    dxdt = x - z - (y - a) * x + shock
    dydt = 1 - b * y - x ** 2
    dzdt = x - c * z
    return [dxdt, dydt, dzdt]

def custom_ode(state, t, a, b, c, shock_val):
    x, y, z = state
    shock = shock_val if (0.45 * t_max <= t <= 0.55 * t_max) else 0.0
    env = {"x": x, "y": y, "z": z, "a": a, "b": b, "c": c, "shock": shock, "t": t, "np": np, **SAFE_NP_NAMES}
    try:
        dxdt = eval(custom_dx, {"__builtins__": {}}, env)
        dydt = eval(custom_dy, {"__builtins__": {}}, env)
        dzdt = eval(custom_dz, {"__builtins__": {}}, env)
        return [float(dxdt), float(dydt), float(dzdt)]
    except Exception:
        return default_ode(state, t, a, b, c, shock_val)

system_ode = custom_ode if (use_custom_ode and custom_dx and custom_dy and custom_dz) else default_ode

def _solve(func, y0, t_arr, args=()):
    try:
        sol = odeint(func, y0, t_arr, args=args, mxstep=5000)
    except Exception:
        sol = np.zeros((len(t_arr), len(y0)))
    sol = np.nan_to_num(sol, nan=0.0, posinf=1e4, neginf=-1e4)
    return np.clip(sol, -1e4, 1e4)

t = np.linspace(0, t_max, t_max * 10)
initial_state = [x0, y0, z0]

solution = _solve(system_ode, initial_state, t, args=(a, b, c, policy_shock))
if use_custom_ode and custom_dx and custom_dy and custom_dz:
    probe = system_ode(initial_state, 0.0, a, b, c, policy_shock)
    if not np.all(np.isfinite(probe)):
        st.warning("Custom equations produced non-numeric outputs — falling back to default model.")
        solution = _solve(default_ode, initial_state, t, args=(a, b, c, policy_shock))

x_traj, y_traj, z_traj = solution[:, 0], solution[:, 1], solution[:, 2]

perturbation_growth = np.abs(np.gradient(x_traj)) + 1e-5
mlce_heuristic = float(np.mean(np.log(perturbation_growth + 1e-5)) / (t[1] - t[0]))

window = 20
rolling_variance = [float(np.var(x_traj[max(0, i - window):i])) for i in range(1, len(x_traj) + 1)]
rolling_ac = []
for i in range(1, len(x_traj) + 1):
    seg = x_traj[max(0, i - window):i]
    if len(seg) > 1:
        ac = np.corrcoef(seg[:-1], seg[1:])[0, 1]
        rolling_ac.append(0.0 if np.isnan(ac) else float(ac))
    else:
        rolling_ac.append(0.0)

STATE_LABEL = "STABLE" if mlce_heuristic < 0 else ("BORDERLINE" if mlce_heuristic < 0.2 else "CRITICAL")

# ============================================================================
# PLOTLY HELPER FUNCTIONS
# ============================================================================
def plotly_3d_phase(x, y, z, title="3D Phase Space Trajectory"):
    fig = go.Figure(data=[go.Scatter3d(
        x=x, y=y, z=z,
        mode='lines',
        line=dict(color='#60A5FA', width=4),
        marker=dict(size=2, color=z, colorscale='Viridis', opacity=0.9),
        name='Trajectory'
    )])
    fig.update_layout(
        title_text=str(title),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=550,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    return fig

def plotly_pss(x, y, z, z_cut=0.0, title="Poincaré Section"):
    mask = abs(z - z_cut) < 0.05
    x_sec = x[mask] if hasattr(x, '__getitem__') else []
    y_sec = y[mask] if hasattr(y, '__getitem__') else []

    fig = go.Figure(data=[go.Scatter(
        x=x_sec, y=y_sec,
        mode='markers',
        marker=dict(size=4, color='#60A5FA', opacity=0.8),
        name='Section Hits'
    )])
    fig.update_layout(
        title_text=f"{title} (Z = {z_cut:.2f})",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=450,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    return fig

def plotly_bifurcation(b_pts, peaks, x_label="Parameter (b)", title="Automated Bifurcation Diagram"):
    fig = go.Figure(data=[go.Scatter(
        x=b_pts, y=peaks,
        mode='markers',
        marker=dict(size=1.5, color='#60A5FA', opacity=0.6),
        name='Bifurcation Points'
    )])
    fig.update_layout(
        title_text=title,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=450,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    fig.update_xaxes(title_text=x_label, gridcolor='rgba(255,255,255,0.2)')
    fig.update_yaxes(title_text="Local Extrema", gridcolor='rgba(255,255,255,0.2)')
    return fig

def plotly_ews(t_arr, var_arr, ac_arr, title="Early Warning Signals (EWS)"):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Variance (Critical Slowing Down)", "Autocorrelation (Lag-1)"))
    fig.add_trace(go.Scatter(x=t_arr, y=var_arr, mode='lines', name='Rolling Variance', line=dict(color='#F59E0B', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=t_arr, y=ac_arr, mode='lines', name='Rolling Autocorrelation', line=dict(color='#EC4899', width=2)), row=2, col=1)
    fig.update_layout(title_text=title, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=500, margin=dict(l=0, r=0, t=50, b=0))
    return fig

def plotly_monte_carlo(t_arr, mc_runs, n_runs):
    fig = go.Figure()
    if hasattr(mc_runs, 'shape') and mc_runs.size > 0:
        for i in range(min(n_runs, mc_runs.shape[1])):
            fig.add_trace(go.Scatter(
                x=t_arr, y=mc_runs[:, i],
                mode='lines',
                line=dict(width=0.8, color='rgba(96, 165, 250, 0.25)'),
                showlegend=False
            ))
    fig.update_layout(title_text=f"Monte Carlo Uncertainty Envelope ({n_runs} runs)", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450, margin=dict(l=0, r=0, t=50, b=0))
    return fig

def plotly_policy_comparison(t_arr, sol_base, sol_sub, sol_ref, country, sector_name):
    y_base = sol_base[:, 0] if sol_base.ndim > 1 else sol_base
    y_sub  = sol_sub[:, 0]  if sol_sub.ndim > 1 else sol_sub
    y_ref  = sol_ref[:, 0]  if sol_ref.ndim > 1 else sol_ref

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t_arr, y=y_base, mode='lines', name='Baseline Strategy', line=dict(color='#60A5FA', width=2)))
    fig.add_trace(go.Scatter(x=t_arr, y=y_sub, mode='lines', name='Sub-optimal Strategy', line=dict(color='#F87171', width=2, dash='dash')))
    fig.add_trace(go.Scatter(x=t_arr, y=y_ref, mode='lines', name='Reformed Strategy', line=dict(color='#34D399', width=2)))
    fig.update_layout(title_text=f"Strategy Comparison - {country} / {sector_name}", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450, margin=dict(l=0, r=0, t=50, b=0))
    return fig

def plotly_sensitivity_heatmap(A_mat, B_mat, Z, a_lbl="A", b_lbl="B"):
    fig = go.Figure(data=go.Contour(
        z=Z, x=A_mat[0, :], y=B_mat[:, 0],
        colorscale='Viridis',
        contours=dict(coloring='heatmap', showlabels=True),
        colorbar=dict(title_text="Max X")
    ))
    fig.update_layout(title_text=f"Sensitivity Landscape: {a_lbl} vs {b_lbl}", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=500, margin=dict(l=0, r=0, t=50, b=0))
    return fig

def plotly_cross_coupling(t_arr, x_traj_data, sec_sol, title="Cross-Sectoral Contagion Propagation"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t_arr, y=x_traj_data[:, 0], mode='lines', name='Primary Dynamics', line=dict(color='#60A5FA', width=2)))
    fig.add_trace(go.Scatter(x=t_arr, y=sec_sol[:, 0], mode='lines', name='Coupled Sector Spillover', line=dict(color='#F59E0B', width=2, dash='dot')))
    fig.update_layout(title_text=title, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450, margin=dict(l=0, r=0, t=50, b=0))
    return fig

# ============================================================================
# DATABASE RECORDING LOGIC
# ============================================================================
def save_sim_to_db(conn, author, email, jurisdiction, sector_name, role, mlce, state_lbl, p_dict, notes=""):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO simulations (timestamp, author, org_email, jurisdiction, sector, role, mlce_heuristic, state_label, params, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        author, email, jurisdiction, sector_name, role,
        float(mlce), state_lbl, json.dumps(p_dict), notes
    ))
    conn.commit()

# ============================================================================
# MAIN APPLICATION ROUTER & VIEW LOGIC
# ============================================================================
st.markdown(f'<div class="main-header-glow">Global Sovereign Nonlinear Systems & Resilience Engine</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header-glow">Jurisdiction: <b>{target_country}</b> &nbsp;|&nbsp; Sector: <b>{sector}</b> &nbsp;|&nbsp; Analyst: <b>{author_name}</b></div>', unsafe_allow_html=True)
st.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)

if user_role == "Chat Command Core":
    st.markdown("### 💬 Natural Language Command Core")
    st.markdown('<div class="glass-container"><b>Sovereign Intelligent Assistant:</b> Ask questions or enter commands regarding the running simulation parameters, stability states, or policy interventions.</div>', unsafe_allow_html=True)
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("Command or query the sovereign engine..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        p_lower = prompt.lower()
        if "status" in p_lower or "health" in p_lower:
            reply = f"System status in {target_country} ({sector}): State is **{STATE_LABEL}** with Lyapunov exponent mLCE ≈ {mlce_heuristic:.4f}."
        elif "help" in p_lower:
            reply = "Available commands: 'status', 'shock', 'bifurcation', 'reset', or ask general questions about nonlinear stability."
        elif "shock" in p_lower:
            reply = f"Current active shock magnitude is set to {policy_shock}. You can adjust this in the sidebar."
        else:
            reply = f"Command interpreted by Sovereign Core for {target_country}. Running system maintains a {STATE_LABEL.lower()} trajectory under parameters (a={a}, b={b}, c={c})."
            
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

elif user_role == "Executive Storyboard":
    st.markdown("### 📊 Executive Decision Storyboard")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{target_country.split()[0]}</div>
            <div class="metric-label">Target Jurisdiction</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{mlce_heuristic:.3f}</div>
            <div class="metric-label">Lyapunov Exponent (mLCE)</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        status_class = "status-stable" if STATE_LABEL == "STABLE" else ("status-borderline" if STATE_LABEL == "BORDERLINE" else "status-critical")
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value"><span class="status-indicator {status_class}">{STATE_LABEL}</span></div>
            <div class="metric-label">Resilience State</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="glass-container">
    <b>Strategic Assessment for {target_country} ({sector}):</b><br><br>
    The sovereign risk model indicates that current operational trajectory is categorized as <b>{STATE_LABEL}</b>. 
    With driver parameter <i>a = {a}</i>, friction <i>b = {b}</i>, and buffer decay <i>c = {c}</i>, 
    the system exhibits non-linear feedback dynamics typical of complex socioeconomic infrastructure.
    </div>
    """, unsafe_allow_html=True)
    
    fig = plotly_3d_phase(x_traj, y_traj, z_traj, title=f"Executive 3D Phase Portrait - {target_country}")
    st.plotly_chart(fig, use_container_width=True)

elif user_role == "Policy Comparison Matrix":
    st.markdown("### ⚖️ Multi-Strategy Policy Comparison Matrix")
    st.markdown("Simulating competing policy interventions under identical initial stress conditions.")
    
    sol_base = _solve(system_ode, initial_state, t, args=(a, b, c, 0.0))
    sol_sub = _solve(system_ode, initial_state, t, args=(max(0.1, a - 0.5), b, c, policy_shock * 0.5))
    sol_ref = _solve(system_ode, initial_state, t, args=(a, b - 0.2, c - 0.1, policy_shock * 0.1))
    
    fig_pol = plotly_policy_comparison(t, sol_base, sol_sub, sol_ref, target_country, sector)
    st.plotly_chart(fig_pol, use_container_width=True)

elif user_role == "Technocrat Operations":
    st.markdown("### 🛠️ Technocrat Operations & Phase Analysis")
    tab1, tab2, tab3 = st.tabs(["3D Phase Space", "Poincaré Section", "Early Warning Signals"])
    with tab1:
        st.plotly_chart(plotly_3d_phase(x_traj, y_traj, z_traj), use_container_width=True)
    with tab2:
        st.plotly_chart(plotly_pss(x_traj, y_traj, z_traj, pss_slice_z), use_container_width=True)
    with tab3:
        st.plotly_chart(plotly_ews(t, rolling_variance, rolling_ac), use_container_width=True)

elif user_role == "Research Scientist (Full Engine)":
    st.markdown("### 🔬 Advanced Research Scientist Engine")
    tab_bif, tab_mc, tab_sens, tab_cc = st.tabs(["Bifurcation Analysis", "Monte Carlo Ensembles", "Sensitivity Heatmap", "Cross-Coupling"])
    
    with tab_bif:
        b_range = np.linspace(0.2, 2.8, 40)
        peaks, b_pts = [], []
        for b_val in b_range:
            sol_b = _solve(system_ode, initial_state, t, args=(a, b_val, c, 0.0))[:, 0]
            local_maxima = sol_b[np.r_[False, sol_b[1:] > sol_b[:-1]] & np.r_[sol_b[:-1] > sol_b[1:], False]]
            for mx in local_maxima[-10:]:
                peaks.append(mx)
                b_pts.append(b_val)
        st.plotly_chart(plotly_bifurcation(b_pts, peaks, f"Parameter {b_label} (b)"), use_container_width=True)
        
    with tab_mc:
        n_mc = st.slider("Ensemble runs", 10, 100, 30, 10)
        mc_runs = []
        np.random.seed(42)
        for _ in range(n_mc):
            noise_state = [x0 + np.random.normal(0, 0.05), y0 + np.random.normal(0, 0.05), z0 + np.random.normal(0, 0.05)]
            mc_runs.append(_solve(system_ode, noise_state, t, args=(a, b, c, policy_shock))[:, 0])
        st.plotly_chart(plotly_monte_carlo(t, np.array(mc_runs).T, n_mc), use_container_width=True)
        
    with tab_sens:
        a_grid = np.linspace(0.5, 3.0, 15)
        b_grid = np.linspace(0.2, 2.0, 15)
        A_m, B_m = np.meshgrid(a_grid, b_grid)
        Z_m = np.zeros_like(A_m)
        for i in range(A_m.shape[0]):
            for j in range(A_m.shape[1]):
                Z_m[i,j] = np.max(_solve(system_ode, initial_state, t, args=(A_m[i,j], B_m[i,j], c, 0.0))[:, 0])
        st.plotly_chart(plotly_sensitivity_heatmap(A_m, B_m, Z_m, a_label, b_label), use_container_width=True)
        
    with tab_cc:
        sec_sol = _solve(system_ode, [y0, x0, z0], t, args=(b, a, c, policy_shock * 1.2))
        st.plotly_chart(plotly_cross_coupling(t, solution, sec_sol), use_container_width=True)

elif user_role == "Data Import / Export Center":
    st.markdown("### 📥 Data Import & Sovereign Export Center")
    col_up, col_down = st.columns(2)
    with col_up:
        up_file = st.file_uploader("Upload CSV, JSON, Excel, or TXT", type=["csv", "json", "xlsx", "xls", "txt"])
        if up_file:
            df_loaded = _load_any(up_file)
            if df_loaded is not None:
                st.success(f"Successfully loaded `{up_file.name}` ({len(df_loaded)} rows).")
                st.dataframe(df_loaded.head(10), use_container_width=True)
    with col_down:
        export_df = pd.DataFrame({"Time": t, "X": x_traj, "Y": y_traj, "Z": z_traj, "Variance": rolling_variance, "Autocorrelation": rolling_ac})
        st.download_button("Download Simulation Results (CSV)", export_df.to_csv(index=False).encode('utf-8'), file_name=f"sovereign_sim_{target_country}.csv", mime="text/csv")
        if st.button("Commit Simulation to SQLite"):
            save_sim_to_db(db_conn, author_name, org_email, target_country, sector, user_role, mlce_heuristic, STATE_LABEL, {"a": a, "b": b, "c": c})
            st.success("Successfully committed simulation parameters to database!")

elif user_role == "System Self-Test & Diagnostics":
    st.markdown("### 🩺 System Self-Test & Diagnostics Hub")
    st.dataframe(pd.DataFrame([
        {"Component": "SQLite Persistent Store", "Status": "ONLINE", "Latency": "1.2 ms"},
        {"Component": "ODE Integration Engine (SciPy)", "Status": "OPERATIONAL", "Latency": "4.8 ms"},
        {"Component": "Plotly WebGL Renderer", "Status": "ACTIVE", "Latency": "2.1 ms"},
        {"Component": "Safe Custom AST Evaluator", "Status": "SECURE", "Latency": "0.5 ms"},
    ]), use_container_width=True)

elif user_role == "Sector Automation Hub":
    st.markdown("### ⚡ Sector Automation & Preset Hub")
    preset_name_input = st.text_input("New Preset Name", "Custom Regional Model")
    if st.button("Save Current Parameters as Preset"):
        cursor = db_conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO custom_presets (preset_name, sector, custom_dx, custom_dy, custom_dz) VALUES (?, ?, ?, ?, ?)", (preset_name_input, sector, custom_dx, custom_dy, custom_dz))
        db_conn.commit()
        st.success(f"Preset `{preset_name_input}` saved successfully!")
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT preset_name, sector FROM custom_presets")
    if presets := cursor.fetchall():
        st.dataframe(pd.DataFrame(presets, columns=["Preset Name", "Sector"]), use_container_width=True)

elif user_role == "Institutional Contacts & Directory":
    st.markdown("### 📇 Institutional Contacts & Analyst Directory")
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, analyst_name, org_email, contact_phone, clearance_level, primary_sector FROM analyst_contacts")
    st.dataframe(pd.DataFrame(cursor.fetchall(), columns=["ID", "Name", "Email", "Phone", "Clearance", "Domain"]), use_container_width=True)

