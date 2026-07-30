import datetime
import io
import json
import sqlite3
import hashlib
import ast
import numpy as np
import pandas as pd
import streamlit as st
from scipy.integrate import odeint, solve_ivp
from scipy.fft import fft, fftfreq

# PDF Generation Dependencies
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# ============================================================================
# DATABASE INITIALIZATION & AUDIT LOGGING
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user TEXT,
            action TEXT,
            details TEXT
        )
    """)
    
    # Seed Initial Institutional Contacts with Hashed Passkeys
    def hash_key(key_str):
        return hashlib.sha256(key_str.encode()).hexdigest()

    cursor.execute("""
        INSERT OR IGNORE INTO analyst_contacts (analyst_name, org_email, contact_phone, clearance_level, primary_sector, vault_hash)
        VALUES 
        ('Kula Chris', 'chrishem@sovereign.org', '+256 700 000000', 'Tier-1 Lead Architect', 'Economics & Sovereign Risk', ?),
        ('Dr. Matsiko', 'matsiko@muni.ac.ug', '+256 772 111222', 'Chief Scientific Director', 'Bioinformatics & Systems', ?),
        ('Ocircan Darius', 'darius@sovereign.org', '+256 750 333444', 'Senior Policy Analyst', 'Infrastructure & Grid', ?)
    """, (hash_key('SOV-999-KEY'), hash_key('SCI-888-KEY'), hash_key('POL-777-KEY')))
    conn.commit()
    return conn

db_conn = init_db()

def log_audit(conn, user, action, details):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_log (timestamp, user, action, details)
        VALUES (?, ?, ?, ?)
    """, (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, details))
    conn.commit()

# ============================================================================
# SAFE AST EVALUATOR FOR CUSTOM ODEs
# ============================================================================
class SafeMathEvaluator(ast.NodeVisitor):
    def __init__(self, variables):
        self.variables = variables
        self.allowed_functions = {
            'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
            'exp': np.exp, 'log': np.log, 'sqrt': np.sqrt,
            'abs': np.abs, 'tanh': np.tanh, 'pi': np.pi
        }

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        elif isinstance(node, ast.Num):  # Python < 3.8
            return node.n
        elif isinstance(node, ast.Constant):  # Python >= 3.8
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in self.variables:
                return self.variables[node.id]
            elif node.id in self.allowed_functions:
                return self.allowed_functions[node.id]
            raise NameError(f"Use of unauthorized variable/function: {node.id}")
        elif isinstance(node, ast.BinOp):
            left = self.visit(node.left)
            right = self.visit(node.right)
            if isinstance(node.op, ast.Add): return left + right
            elif isinstance(node.op, ast.Sub): return left - right
            elif isinstance(node.op, ast.Mult): return left * right
            elif isinstance(node.op, ast.Div): return left / right
            elif isinstance(node.op, ast.Pow): return left ** right
            elif isinstance(node.op, ast.Mod): return left % right
            raise TypeError(f"Unsupported binary operator: {type(node.op)}")
        elif isinstance(node, ast.UnaryOp):
            operand = self.visit(node.operand)
            if isinstance(node.op, ast.USub): return -operand
            elif isinstance(node.op, ast.UAdd): return +operand
            raise TypeError(f"Unsupported unary operator: {type(node.op)}")
        elif isinstance(node, ast.Call):
            func = self.visit(node.func)
            args = [self.visit(arg) for arg in node.args]
            return func(*args)
        else:
            raise TypeError(f"Unsupported expression node: {type(node)}")

def safe_eval(expr_str, variables):
    tree = ast.parse(expr_str, mode='eval')
    evaluator = SafeMathEvaluator(variables)
    return evaluator.visit(tree)

# ============================================================================
# PAGE CONFIG + GLASSMORPHISM STYLES
# ============================================================================
st.set_page_config(
    page_title="Global Sovereign Nonlinear Systems & Resilience Engine",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #F8FAFC !important; }
    .stApp { background: linear-gradient(135deg, #070B14 0%, #0F172A 50%, #070B14 100%); background-attachment: fixed; }
    .glass-container {
        background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 20px; padding: 1.5rem; margin-bottom: 1rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); color: #F8FAFC !important;
    }
    .glass-container:hover { border-color: rgba(59, 130, 246, 0.5); box-shadow: 0 12px 48px 0 rgba(0, 0, 0, 0.8); transform: translateY(-1px); }
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 16px; padding: 1.2rem; text-align: center;
        backdrop-filter: blur(10px); box-shadow: 0 4px 20px rgba(0,0,0,0.5); transition: all 0.3s ease;
    }
    .metric-card:hover { border-color: rgba(59, 130, 246, 0.6); transform: scale(1.02); }
    .metric-value { font-size: 2rem; font-weight: 800; background: linear-gradient(90deg, #60A5FA, #A78BFA); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
    .metric-label { font-size: 0.85rem; color: #CBD5E1 !important; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.3rem; font-weight: 600; }
    .status-indicator { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.2rem; border-radius: 9999px; font-weight: 700; font-size: 0.9rem; backdrop-filter: blur(10px); border: 1px solid; }
    .status-stable { background: rgba(22, 101, 52, 0.4); border-color: rgba(74, 222, 128, 0.6); color: #4ADE80 !important; animation: pulse-green 2.5s infinite; }
    .status-borderline { background: rgba(133, 77, 14, 0.4); border-color: rgba(250, 204, 21, 0.6); color: #FACC15 !important; animation: pulse-yellow 2.5s infinite; }
    .status-critical { background: rgba(153, 27, 27, 0.4); border-color: rgba(248, 113, 113, 0.6); color: #F87171 !important; animation: pulse-red 2.5s infinite; }
    @keyframes pulse-green { 0%, 100% { box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.4); } 50% { box-shadow: 0 0 0 12px rgba(74, 222, 128, 0); } }
    @keyframes pulse-yellow { 0%, 100% { box-shadow: 0 0 0 0 rgba(250, 204, 21, 0.4); } 50% { box-shadow: 0 0 0 12px rgba(250, 204, 21, 0); } }
    @keyframes pulse-red { 0%, 100% { box-shadow: 0 0 0 0 rgba(248, 113, 113, 0.4); } 50% { box-shadow: 0 0 0 12px rgba(248, 113, 113, 0); } }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: rgba(15, 23, 42, 0.8); padding: 6px; border-radius: 12px; backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.15); }
    .stTabs [data-baseweb="tab"] { background: transparent; border-radius: 8px; padding: 10px 18px; font-weight: 600; color: #CBD5E1 !important; border: 1px solid transparent; transition: all 0.2s ease; }
    .stTabs [data-baseweb="tab"]:hover { background: rgba(255, 255, 255, 0.1); color: #FFFFFF !important; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #3B82F6, #8B5CF6) !important; color: #FFFFFF !important; border-color: rgba(255, 255, 255, 0.3) !important; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4); }
    .stButton > button { background: linear-gradient(135deg, #3B82F6, #8B5CF6) !important; color: #FFFFFF !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 12px !important; padding: 0.6rem 1.5rem !important; font-weight: 700 !important; transition: all 0.3s ease !important; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3) !important; }
    .stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5) !important; filter: brightness(1.15) !important; }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stNumberInput > div > div > input { background: rgba(15, 23, 42, 0.9) !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 10px !important; color: #F8FAFC !important; font-family: 'Inter', sans-serif !important; font-weight: 500 !important; }
    .stSelectbox > div > div, .stMultiSelect > div > div { background: rgba(15, 23, 42, 0.9) !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; border-radius: 10px !important; color: #F8FAFC !important; }
    section[data-testid="stSidebar"] { background: rgba(7, 11, 20, 0.95) !important; backdrop-filter: blur(24px) !important; -webkit-backdrop-filter: blur(24px) !important; border-right: 1px solid rgba(255, 255, 255, 0.1) !important; }
    .main-header-glow { background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; font-size: 2.4rem; font-weight: 800; letter-spacing: -1px; }
    .sub-header-glow { color: #E2E8F0 !important; font-size: 1.05rem; font-weight: 500; }
    .glass-divider { height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent); margin: 1.5rem 0; }
    .research-card { background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 16px; padding: 1.5rem; height: 100%; transition: all 0.3s ease; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# INITIALIZE SESSION STATE PARAMETERS
# ============================================================================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "Sovereign Intelligence Core online. Type 'help' for available system queries."}]
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def sync_param(key, val):
    st.session_state[key] = val

# ============================================================================
# SIDEBAR CONTROL HUB
# ============================================================================
st.sidebar.markdown("## 🌐 Global Sovereign Command Hub")

with st.sidebar.expander("👤 Institutional & Analyst Details", expanded=True):
    user_role = st.selectbox(
        "Privilege tier",
        [
            "💬 Chat Command Core",
            "👔 Executive Storyboard",
            "⚖️ Policy Comparison Matrix",
            "📊 Technocrat Operations",
            "🔬 Research Scientist (full engine)",
            "📥 Data Import / Export Center",
            "🧪 System Self-Test & Diagnostics",
            "⚡ Sector Automation Hub",
            "📇 Institutional Contacts & Directory",
            "📜 Audit Log & System History",
        ],
    )
    author_name = st.text_input("Author / Analyst Name", "Kula Chris")
    org_email = st.text_input("Organization Email", "chrishem@sovereign.org")
    contact_phone = st.text_input("Contact Phone", "+256 700 000000")
    secure_vault_token = st.text_input("Secure Vault Passkey", type="password", value="SOV-999-KEY")

# Vault Hash Verification (RBAC)
token_hash = hashlib.sha256(secure_vault_token.encode()).hexdigest()
cursor = db_conn.cursor()
cursor.execute("SELECT clearance_level FROM analyst_contacts WHERE vault_hash = ?", (token_hash,))
auth_res = cursor.fetchone()
is_authenticated = auth_res is not None
clearance_level = auth_res[0] if is_authenticated else "Unverified Observer"

if is_authenticated:
    st.sidebar.success(f"🔐 Authenticated: {clearance_level}")
else:
    st.sidebar.warning("⚠️ Passkey Unverified — Restricted Mode")

st.sidebar.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown("### 📍 Jurisdiction & Domain")

PRESET_COUNTRIES = [
    "🇺🇬 Uganda", "🇰🇪 Kenya", "🇷🇼 Rwanda", "🇳🇬 Nigeria", "🇿🇦 South Africa",
    "🇬🇭 Ghana", "🇪🇹 Ethiopia", "🇹ℤ Tanzania", "🇪🇬 Egypt",
    "🇺🇸 United States", "🇬🇧 United Kingdom", "🇫🇷 France", "🇩🇪 Germany",
    "🇯🇵 Japan", "🇨🇳 China", "🇮🇳 India", "🇧🇷 Brazil", "🇨🇦 Canada",
    "🇦🇺 Australia", "🌐 Global / Multi-State Aggregate",
]

region_mode = st.sidebar.radio("Jurisdiction scope", ["Choose from list", "Type any country / region"], horizontal=True)
target_country = st.sidebar.selectbox("Country / Territory", PRESET_COUNTRIES, index=0) if region_mode == "Choose from list" else st.sidebar.text_input("Type region", "e.g. Vietnam")

PRESET_SECTORS = {
    "💰 Economics & Finance (Huang-Li model)": ("a", "Savings / growth rate", "b", "Investment cost", "c", "Market elasticity"),
    "🏥 Healthcare: Hospital surge & capacity": ("a", "Patient influx rate", "b", "ICU bed burnout", "c", "Staff fatigue decay"),
    "🦠 Epidemiology: Outbreak dynamics": ("a", "Transmission rate", "b", "Recovery rate", "c", "Waning immunity"),
    "🎓 Education: Tuition & institutional cashflow": ("a", "Tuition collection speed", "b", "Operational overhead", "c", "Reserve depletion"),
    "🌾 Agriculture: Food security & yield risk": ("a", "Climate stress index", "b", "Supply-chain friction", "c", "Reserve depletion"),
    "🧬 Bioinformatics: Gene regulatory networks": ("a", "Expression drive", "b", "Feedback damping", "c", "Mutation pressure"),
    "🏦 Treasury: Fiscal deficit & contagion": ("a", "Stress multiplier", "b", "Structural friction", "c", "Damping coefficient"),
    "⚡ Infrastructure: Power / grid reliability": ("a", "Demand surge", "b", "Load friction", "c", "Buffer capacity"),
    "🌊 Environmental: Predator-prey / hydrology": ("a", "Growth rate", "b", "Consumption rate", "c", "Recovery rate"),
}

sector_mode = st.sidebar.radio("Sector scope", ["Choose from list", "Type any custom sector"], horizontal=True)
if sector_mode == "Choose from list":
    sector = st.sidebar.selectbox("Institutional sector", list(PRESET_SECTORS.keys()))
    a_label, a_desc, b_label, b_desc, c_label, c_desc = PRESET_SECTORS[sector]
else:
    sector = st.sidebar.text_input("Describe sector", "e.g. Satellite telemetry")
    a_label, a_desc, b_label, b_desc, c_label, c_desc = "a", "Growth term", "b", "Friction term", "c", "Buffer term"

st.sidebar.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown(f"### ⚙️ Parameters — {sector}")
a = st.sidebar.slider(f"{a_label} — {a_desc}", 0.1, 5.0, st.session_state.get("param_a", 1.5), 0.1, key="param_a")
b = st.sidebar.slider(f"{b_label} — {b_desc}", 0.0, 3.0, st.session_state.get("param_b", 0.9), 0.1, key="param_b")
c = st.sidebar.slider(f"{c_label} — {c_desc}", 0.0, 3.0, st.session_state.get("param_c", 1.0), 0.1, key="param_c")

st.sidebar.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown("### 🛠️ Solver & Integration Configuration")
solver_type = st.sidebar.selectbox("Numerical Integrator Engine", ["SciPy odeint (Default)", "RK45 (Explicit Runge-Kutta)", "Radau (Stiff Systems)", "LSODA (Adaptive)"])

st.sidebar.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)
st.sidebar.markdown("### 🎯 Initial conditions & shock")
x0 = st.sidebar.number_input("Initial x₀", value=0.10, format="%.3f")
y0 = st.sidebar.number_input("Initial y₀", value=0.10, format="%.3f")
z0 = st.sidebar.number_input("Initial z₀", value=0.10, format="%.3f")
policy_shock = st.sidebar.slider("Inject shock magnitude", -3.0, 3.0, 0.0, 0.1)
t_max = st.sidebar.slider("Simulation horizon (steps)", 50, 500, 200, 10)

use_custom_ode = st.sidebar.checkbox("✏️ Use custom ODE equations")
custom_dx = custom_dy = custom_dz = ""
if use_custom_ode:
    st.sidebar.caption("Variables: x, y, z, a, b, c, shock, t, sin, cos, exp, log, sqrt")
    custom_dx = st.sidebar.text_input("dx/dt =", "x - z - (y - a) * x + shock")
    custom_dy = st.sidebar.text_input("dy/dt =", "1 - b * y - x**2")
    custom_dz = st.sidebar.text_input("dz/dt =", "x - c * z")

pss_slice_z = st.sidebar.slider("✂️ Poincaré cut plane (Z threshold)", float(z0 - 2.0), float(z0 + 2.0), float(z0), 0.05)

# ============================================================================
# SAFE NUMERICAL MODEL CORE
# ============================================================================
def default_ode_system(t_val, state, a_val, b_val, c_val, shock_val):
    x, y, z = state
    shock = shock_val if (0.45 * t_max <= t_val <= 0.55 * t_max) else 0.0
    dxdt = x - z - (y - a_val) * x + shock
    dydt = 1 - b_val * y - x ** 2
    dzdt = x - c_val * z
    return [dxdt, dydt, dzdt]

def custom_ode_system(t_val, state, a_val, b_val, c_val, shock_val):
    x, y, z = state
    shock = shock_val if (0.45 * t_max <= t_val <= 0.55 * t_max) else 0.0
    env = {"x": x, "y": y, "z": z, "a": a_val, "b": b_val, "c": c_val, "shock": shock, "t": t_val}
    try:
        dxdt = safe_eval(custom_dx, env)
        dydt = safe_eval(custom_dy, env)
        dzdt = safe_eval(custom_dz, env)
        return [float(dxdt), float(dydt), float(dzdt)]
    except Exception:
        return default_ode_system(t_val, state, a_val, b_val, c_val, shock_val)

def execute_solve(y_init, t_array, a_v, b_v, c_v, shock_v, solver="SciPy odeint (Default)"):
    chosen_ode = custom_ode_system if (use_custom_ode and custom_dx and custom_dy and custom_dz) else default_ode_system
    try:
        if solver == "SciPy odeint (Default)":
            def ode_wrapper(state, t_in, a_in, b_in, c_in, s_in):
                return chosen_ode(t_in, state, a_in, b_in, c_in, s_in)
            sol = odeint(ode_wrapper, y_init, t_array, args=(a_v, b_v, c_v, shock_v), mxstep=5000)
        else:
            method_map = {"RK45 (Explicit Runge-Kutta)": "RK45", "Radau (Stiff Systems)": "Radau", "LSODA (Adaptive)": "LSODA"}
            res = solve_ivp(
                fun=lambda t_in, y_in: chosen_ode(t_in, y_in, a_v, b_v, c_v, shock_v),
                t_span=(t_array[0], t_array[-1]),
                y0=y_init,
                t_eval=t_array,
                method=method_map.get(solver, "RK45")
            )
            sol = res.y.T if res.success else np.zeros((len(t_array), 3))
    except Exception:
        sol = np.zeros((len(t_array), 3))
    sol = np.nan_to_num(sol, nan=0.0, posinf=1e4, neginf=-1e4)
    return np.clip(sol, -1e4, 1e4)

t = np.linspace(0, t_max, t_max * 10)
initial_state = [x0, y0, z0]
solution = execute_solve(initial_state, t, a, b, c, policy_shock, solver=solver_type)

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

# Log execution audit
log_audit(db_conn, author_name, "SIMULATION_RUN", f"Jurisdiction: {target_country}, Sector: {sector}, mLCE: {mlce_heuristic:.4f}")

# ============================================================================
# PLOTLY VISUALIZATIONS
# ============================================================================
def plotly_3d_phase(x, y, z, title="3D Phase Space Trajectory"):
    fig = go.Figure(data=[go.Scatter3d(
        x=x, y=y, z=z, mode='lines',
        line=dict(color='#60A5FA', width=4),
        marker=dict(size=2, color=z, colorscale='Viridis', opacity=0.9), name='Trajectory'
    )])
    fig.update_layout(title_text=str(title), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=550, margin=dict(l=0, r=0, t=50, b=0))
    return fig

def plotly_pss(x, y, z, z_cut=0.0, title="Poincaré Section"):
    mask = abs(z - z_cut) < 0.05
    x_sec, y_sec = x[mask], y[mask]
    fig = go.Figure(data=[go.Scatter(x=x_sec, y=y_sec, mode='markers', marker=dict(size=4, color='#60A5FA', opacity=0.8), name='Section Hits')])
    fig.update_layout(title_text=f"{title} (Z = {z_cut:.2f})", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450, margin=dict(l=0, r=0, t=50, b=0))
    return fig

def plotly_fft_psd(t_arr, signal, title="Fourier & Power Spectral Density (PSD) Analysis"):
    N = len(signal)
    dt = t_arr[1] - t_arr[0]
    yf = fft(signal)
    xf = fftfreq(N, dt)[:N//2]
    psd = 2.0/N * np.abs(yf[0:N//2])
    
    fig = go.Figure(data=[go.Scatter(x=xf, y=psd, mode='lines', line=dict(color='#A78BFA', width=2), name='Spectral Power')])
    fig.update_layout(title_text=title, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450, margin=dict(l=0, r=0, t=50, b=0))
    fig.update_xaxes(title_text="Frequency (Hz)", gridcolor='rgba(255,255,255,0.2)')
    fig.update_yaxes(title_text="Power Spectral Density", gridcolor='rgba(255,255,255,0.2)')
    return fig

def plotly_bifurcation(b_pts, peaks, x_label="Parameter (b)", title="Automated Bifurcation Diagram"):
    fig = go.Figure(data=[go.Scatter(x=b_pts, y=peaks, mode='markers', marker=dict(size=1.5, color='#60A5FA', opacity=0.6), name='Bifurcation Points')])
    fig.update_layout(title_text=title, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450, margin=dict(l=0, r=0, t=50, b=0))
    fig.update_xaxes(title_text=x_label, gridcolor='rgba(255,255,255,0.2)')
    fig.update_yaxes(title_text="Local Maxima / Minima", gridcolor='rgba(255,255,255,0.2)')
    return fig

def plotly_ews(t, rolling_variance, rolling_ac, title="Early Warning Signals (EWS)"):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Variance (Critical Slowing Down)", "Autocorrelation (Lag-1)"))
    fig.add_trace(go.Scatter(x=t, y=rolling_variance, mode='lines', name='Rolling Variance', line=dict(color='#F59E0B', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=rolling_ac, mode='lines', name='Rolling Autocorrelation', line=dict(color='#EC4899', width=2)), row=2, col=1)
    fig.update_layout(title_text=title, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=500, margin=dict(l=0, r=0, t=50, b=0))
    return fig

# ============================================================================
# EXECUTIVE PDF REPORT GENERATOR
# ============================================================================
def generate_pdf_brief(author, jurisdiction, sector, state_lbl, mlce, params):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    story = []
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor("#0F172A"), spaceAfter=12)
    meta_style = ParagraphStyle('MetaStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#475569"), spaceAfter=18)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=11, leading=15, spaceAfter=12)
    
    story.append(Paragraph("Sovereign Intelligence Executive Brief", title_style))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | <b>Analyst:</b> {author}", meta_style))
    
    data = [
        ["Jurisdiction Scope", jurisdiction],
        ["Institutional Sector", sector],
        ["Resilience State", state_lbl],
        ["Lyapunov Exponent (mLCE)", f"{mlce:.4f}"],
        ["Parameters (a, b, c)", f"a={params['a']}, b={params['b']}, c={params['c']}"]
    ]
    t_table = Table(data, colWidths=[180, 320])
    t_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
    ]))
    story.append(t_table)
    story.append(Spacer(1, 18))
    
    story.append(Paragraph("<b>Executive Assessment:</b>", body_style))
    story.append(Paragraph(f"The sovereign non-linear systems engine evaluated <b>{jurisdiction}</b> within the <b>{sector}</b> domain. "
                           f"The active trajectory displays a state classification of <b>{state_lbl}</b>. "
                           f"Quantitative risk models recommend continuous monitoring of parameter boundaries and critical thresholds.", body_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ============================================================================
# MAIN APPLICATION ROUTER
# ============================================================================
st.markdown(f'<div class="main-header-glow">Global Sovereign Nonlinear Systems & Resilience Engine</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header-glow">Jurisdiction: <b>{target_country}</b> &nbsp;|&nbsp; Sector: <b>{sector}</b> &nbsp;|&nbsp; Analyst: <b>{author_name}</b> ({clearance_level})</div>', unsafe_allow_html=True)
st.markdown('<div class="glass-divider"></div>', unsafe_allow_html=True)

if "Chat Command" in user_role:
    st.markdown("### 💬 Natural Language Command Core")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("Command or query the sovereign engine..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
            
        p_lower = prompt.lower()
        if "status" in p_lower:
            reply = f"System status for {target_country}: State is **{STATE_LABEL}** (mLCE ≈ {mlce_heuristic:.4f}). Integrator: `{solver_type}`."
        elif "help" in p_lower:
            reply = "Supported queries: 'status', 'shock', 'bifurcation', 'solver', or general dynamic trajectory analysis."
        else:
            reply = f"Processed command for {target_country} ({sector}). Trajectory is {STATE_LABEL} under (a={a}, b={b}, c={c})."
            
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"): st.markdown(reply)

elif "Executive Storyboard" in user_role:
    st.markdown("### 👔 Executive Decision Storyboard")
    
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(f'<div class="metric-card"><div class="metric-value">{target_country.split()[0]}</div><div class="metric-label">Target Jurisdiction</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-card"><div class="metric-value">{mlce_heuristic:.3f}</div><div class="metric-label">Lyapunov Exponent (mLCE)</div></div>', unsafe_allow_html=True)
    with col3:
        status_class = "status-stable" if STATE_LABEL == "STABLE" else ("status-borderline" if STATE_LABEL == "BORDERLINE" else "status-critical")
        st.markdown(f'<div class="metric-card"><div class="metric-value"><span class="status-indicator {status_class}">{STATE_LABEL}</span></div><div class="metric-label">Resilience State</div></div>', unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Executive PDF Export Trigger
    pdf_bytes = generate_pdf_brief(author_name, target_country, sector, STATE_LABEL, mlce_heuristic, {"a": a, "b": b, "c": c})
    st.download_button("📄 Download Formatted Executive PDF Brief", data=pdf_bytes, file_name=f"Executive_Brief_{target_country.replace(' ', '_')}.pdf", mime="application/pdf")
    
    fig = plotly_3d_phase(x_traj, y_traj, z_traj, title=f"Executive Phase Portrait — {target_country}")
    st.plotly_chart(fig, use_container_width=True)

elif "Technocrat Operations" in user_role:
    st.markdown("### 📊 Technocrat Operations & Phase Analysis")
    tab1, tab2, tab3, tab4 = st.tabs(["3D Phase Space", "Poincaré Section", "Fourier / PSD Spectrum", "Early Warning Signals"])
    with tab1: st.plotly_chart(plotly_3d_phase(x_traj, y_traj, z_traj), use_container_width=True)
    with tab2: st.plotly_chart(plotly_pss(x_traj, y_traj, z_traj, pss_slice_z), use_container_width=True)
    with tab3: st.plotly_chart(plotly_fft_psd(t, x_traj), use_container_width=True)
    with tab4: st.plotly_chart(plotly_ews(t, rolling_variance, rolling_ac), use_container_width=True)

elif "Audit Log & System History" in user_role:
    st.markdown("### 📜 Live System Log & Audit Trail")
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, timestamp, user, action, details FROM audit_log ORDER BY id DESC LIMIT 50")
    logs = cursor.fetchall()
    st.dataframe(pd.DataFrame(logs, columns=["ID", "Timestamp", "User", "Action", "Details"]), use_container_width=True)

else:
    st.info("Select specific privilege tiers in the sidebar to access additional functional modules.")

