import security_guard
iimport security_guard
security_guard.verify_access()

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
# 1. DATABASE INITIALIZATION (Infrastructure Command Store)
# ============================================================================
def init_infrastructure_db():
    conn = sqlite3.connect("infrastructure_command_engine.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grid_simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            sector TEXT,
            cascade_risk REAL,
            status_label TEXT,
            payload TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS critical_substations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            substation_name TEXT,
            load_mw REAL,
            capacity_mw REAL,
            status TEXT,
            operator_contact TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO critical_substations (substation_name, load_mw, capacity_mw, status, operator_contact)
        VALUES 
        ('Substation Alpha (Capital)', 420.5, 500.0, 'Optimal', 'ops-alpha@grid.net'),
        ('Substation Beta (Industrial Zone)', 680.0, 750.0, 'High Load', 'ops-beta@grid.net'),
        ('Substation Gamma (Hydro Hub)', 310.2, 600.0, 'Stable', 'ops-gamma@grid.net')
    """)
    conn.commit()
    return conn

db_conn = init_infrastructure_db()

# ============================================================================
# 2. PAGE CONFIGURATION & HIGH-CONTRAST STYLING
# ============================================================================
st.set_page_config(
    page_title="Energy Grids & Infrastructure Resiliency Suite",
    page_icon="⚡",
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
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #F8FAFC !important;
    }
    .stApp {
        background: linear-gradient(135deg, #060b13 0%, #0f172a 50%, #060b13 100%);
        background-attachment: fixed;
    }
    .glass-container {
        background: rgba(17, 28, 46, 0.85);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6);
        color: #F8FAFC !important;
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(17, 28, 46, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00f2fe, #4facfe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #cbd5e1 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.3rem;
        font-weight: 600;
    }
    .main-header-glow {
        background: linear-gradient(90deg, #00f2fe, #4facfe, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -1px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# 3. SIDEBAR CONTROLS & MODULE SELECTOR
# ============================================================================
st.sidebar.markdown("## ⚡ Infrastructure Command Hub")

infra_module = st.sidebar.selectbox(
    "Select Infrastructure Module",
    [
        "Executive Grid & Infrastructure Dashboard",
        "Cascading Power Failure & Stability Simulation",
        "Municipal Water Reservoir Hydrological Strain",
        "Intermittent Renewable Integration & Storage",
        "Smart-Grid Substation Dispatch & Load Balancing",
        "Transmission Line Thermal Overload & Faults",
        "Emergency Interventions & Grid Restoration Matrix"
    ]
)

target_grid_sector = st.sidebar.selectbox("Regional Power Grid Sector", [
    "National Interconnected Grid", "Northern Transmission Corridor", 
    "Capital Metropolitan Grid", "Industrial Export Hub", "Rural Microgrid Network"
])

simulation_hours = st.sidebar.slider("Simulation Horizon (Hours)", 12, 168, 48, 12)
grid_stress_multiplier = st.sidebar.slider("Grid Stress & Peak Demand Multiplier", 0.5, 2.5, 1.1, 0.1)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Core Grid Parameters")
base_demand_mw = st.sidebar.slider("Base System Demand (MW)", 500, 5000, 1850, 100)
renewable_share = st.sidebar.slider("Renewable Penetration (%)", 5.0, 75.0, 32.0, 2.5)
reservoir_capacity = st.sidebar.slider("Water Reservoir Capacity (%)", 20.0, 100.0, 68.5, 2.5)

# ============================================================================
# 4. SIMULATION SOLVER (Cascading Failure ODE & Hydrological Strain)
# ============================================================================
def grid_failure_model(y, t, demand_mult, renewables):
    Instability, StorageLevel, ThermalStrain = y
    # Instability: Grid cascade risk score, StorageLevel: Battery/Hydro buffer, ThermalStrain: Line overload
    dInstability = 0.05 * demand_mult - 0.03 * (renewables * 0.01) + 0.02 * ThermalStrain
    dStorage = -0.04 * demand_mult + 0.02 * (renewables * 0.01)
    dThermal = 0.08 * (demand_mult - 1.0) - 0.01 * StorageLevel
    return [dInstability, dStorage, dThermal]

t_hours = np.linspace(0, simulation_hours, simulation_hours * 2)
initial_grid_state = [0.012, 0.75, 0.20]
grid_solution = odeint(grid_failure_model, initial_grid_state, t_hours, args=(grid_stress_multiplier, renewable_share))

instability_traj, storage_traj, thermal_traj = grid_solution[:, 0], grid_solution[:, 1], grid_solution[:, 2]
current_cascade_risk = float(instability_traj[-1])

# ============================================================================
# 5. MAIN APPLICATION INTERFACE
# ============================================================================
st.markdown(f'<div class="main-header-glow">Energy Grids & Infrastructure Resiliency Suite</div>', unsafe_allow_html=True)
st.markdown(f"**Active Module:** `{infra_module}` &nbsp;|&nbsp; **Grid Sector:** `{target_grid_sector}`")
st.markdown("---")

if infra_module == "Executive Grid & Infrastructure Dashboard":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{max(0.001, current_cascade_risk):.4f}</div>
            <div class="metric-label">Power Grid Cascade Risk</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{reservoir_capacity:.1f}%</div>
            <div class="metric-label">Municipal Water Reservoir</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{renewable_share:.1f}%</div>
            <div class="metric-label">Renewable Penetration</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{base_demand_mw} MW</div>
            <div class="metric-label">Active System Load</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    col_alert1, col_alert2 = st.columns(2)
    with col_alert1:
        st.success("✅ **Renewable Grid Penetration Threshold Safe:** Current load operating within safe tolerance limits; storage buffers are fully primed.")
    with col_alert2:
        st.warning("⚠️ **Thermal Warning:** High peak industrial demand projected in 6 hours; prepare secondary hydro peaking units.")

    fig_exec = go.Figure()
    fig_exec.add_trace(go.Scatter(x=t_hours, y=instability_traj * 100, mode='lines', name='Cascade Failure Risk Index (%)', line=dict(color='#00f2fe', width=3)))
    fig_exec.add_trace(go.Scatter(x=t_hours, y=thermal_traj * 100, mode='lines', name='Transmission Thermal Strain (%)', line=dict(color='#f43f5e', width=3, dash='dash')))
    fig_exec.update_layout(
        title_text=f"Grid Instability & Thermal Overload Projections ({target_grid_sector})",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=450,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    st.plotly_chart(fig_exec, use_container_width=True)

elif infra_module == "Cascading Power Failure & Stability Simulation":
    st.markdown("### ⚡ Cascading Power Failure & System Stability Simulation")
    st.markdown("Simulating N-1 contingency failures, voltage collapse propagation, and automatic load-shedding protocols.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="glass-container">
        <b>Failure Propagation Diagnostics:</b><br><br>
        * <b>Calculated Cascade Risk:</b> {current_cascade_risk:.4f}<br>
        * <b>System Resilience State:</b> {"Stable" if current_cascade_risk < 0.050 else "Critical Alert"}<br>
        * <b>Recommended Action:</b> {"Maintain normal automated frequency regulation." if current_cascade_risk < 0.050 else "Initiate rotational load shedding across industrial corridors."}
        </div>
        """, unsafe_allow_html=True)
    with col2:
        fail_fig = px.line(x=t_hours, y=instability_traj, labels={'x': 'Hours', 'y': 'Cascade Risk Index'}, title="Instability Trajectory Curve")
        fail_fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=320, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fail_fig, use_container_width=True)

elif infra_module == "Municipal Water Reservoir Hydrological Strain":
    st.markdown("### 💧 Municipal Water Reservoir & Hydropower Strain Analysis")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Reservoir Storage Level", f"{reservoir_capacity:.1f}%", delta="+1.5%")
    col2.metric("Inflow vs Outflow Rate", "+420 m³/s", delta="-15 m³/s")
    col3.metric("Hydropower Generation Output", f"{int(base_demand_mw * 0.45)} MW", delta="+25 MW")

    res_df = pd.DataFrame({
        "Reservoir Basin": ["Owen Falls / Victoria Nile", "Mount Elgon Catchment", "Western Crater Lakes", "Southern Gorge Basin"],
        "Storage Level (%)": [reservoir_capacity, 74.2, 82.5, 61.0],
        "Discharge Rate (m³/s)": [1250, 410, 310, 890],
        "Hydrological Status": ["Optimal", "Normal", "High Buffer", "Caution"]
    })
    st.dataframe(res_df, use_container_width=True)

elif infra_module == "Intermittent Renewable Integration & Storage":
    st.markdown("### ☀️ Intermittent Renewable Energy Integration & Battery Storage")
    
    fig_renew = go.Figure()
    fig_renew.add_trace(go.Scatter(x=t_hours, y=storage_traj * 100, mode='lines', name='Battery/Storage Reserve (%)', line=dict(color='#34d399', width=3)))
    fig_renew.add_trace(go.Scatter(x=t_hours, y=np.ones_like(t_hours) * renewable_share, mode='lines', name='Target Renewable Share (%)', line=dict(color='#fbbf24', width=2, dash='dot')))
    fig_renew.update_layout(title_text="Renewable Penetration vs Storage Discharge", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=420, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_renew, use_container_width=True)

elif infra_module == "Smart-Grid Substation Dispatch & Load Balancing":
    st.markdown("### 🎛️ Smart-Grid Substation Dispatch & Load Balancing")
    col1, col2 = st.columns(2)
    col1.metric("Active Substation Nodes", "24 Operational", delta="0")
    col2.metric("Grid Frequency Synchronization", "50.02 Hz", delta="+0.01 Hz")
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT substation_name, load_mw, capacity_mw, status, operator_contact FROM critical_substations")
    subs_data = cursor.fetchall()
    
    subs_df = pd.DataFrame(subs_data, columns=["Substation Facility", "Current Load (MW)", "Max Capacity (MW)", "Operational Status", "Operator Contact"])
    st.dataframe(subs_df, use_container_width=True)

elif infra_module == "Transmission Line Thermal Overload & Faults":
    st.markdown("### 🔌 Transmission Line Thermal Overload & Fault Diagnostics")
    st.markdown("Monitoring conductor sagging, thermal limits, short-circuit currents, and automated breaker reclosing.")
    
    line_df = pd.DataFrame({
        "Transmission Line Corridor": ["Line A (North-South Intertie)", "Line B (Industrial Ring)", "Line C (Hydro Feeder)", "Line D (Capital Loop)"],
        "Thermal Load (%)": [78.5, 92.0, 64.2, 81.0],
        "Conductor Temp (°C)": [68.4, 84.5, 55.0, 71.2],
        "Fault Risk Status": ["Normal", "Warning", "Optimal", "Stable"]
    })
    st.dataframe(line_df, use_container_width=True)

elif infra_module == "Emergency Interventions & Grid Restoration Matrix":
    st.markdown("### 🛡️ Emergency Interventions & Blackstart Restoration Matrix")
    col1, col2, col3 = st.columns(3)
    col1.metric("Blackstart Readiness", "98.4%", delta="+0.4%")
    col2.metric("Spinning Reserve Margin", "340 MW", delta="-15 MW")
    col3.metric("Emergency Response Time", "4.5 Minutes", delta="-0.8 min")

    st.markdown("""
    <div class="glass-container">
    <b>Grid Restoration Advisory:</b><br>
    All spinning reserves are synchronized with regional dispatch centers. In the event of a frequency excursion below 49.5 Hz, automated islanding protocols will isolate critical municipal infrastructure within 300 milliseconds.
    </div>
    """, unsafe_allow_html=True)

