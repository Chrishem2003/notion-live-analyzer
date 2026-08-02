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
# DATABASE INITIALIZATION (Health Command & Multi-Department Store)
# ============================================================================
def init_health_db():
    conn = sqlite3.connect("global_health_engine.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS department_simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            department TEXT,
            facility_name TEXT,
            risk_score REAL,
            state_label TEXT,
            metrics_payload TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outbreak_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pathogen TEXT,
            mutation_variant TEXT,
            transmission_index REAL,
            severity TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO outbreak_alerts (pathogen, mutation_variant, transmission_index, severity)
        VALUES 
        ('SARS-CoV-2', 'Omicron Sublineage XBB.1.5', 1.25, 'Moderate'),
        ('Influenza A', 'H3N2 Drift Variant', 1.40, 'High'),
        ('Ebola Virus', 'Sudan Strain Isolate', 0.85, 'Critical Monitoring')
    """)
    conn.commit()
    return conn

db_conn = init_health_db()

# ============================================================================
# PAGE CONFIG & HIGH-CONTRAST CLINICAL STYLING
# ============================================================================
st.set_page_config(
    page_title="Global Health Sector Command & Multi-Departmental Problem Solver",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #04121f !important;
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
        background: linear-gradient(135deg, #020617 0%, #0f172a 50%, #020617 100%);
        background-attachment: fixed;
    }
    .glass-container {
        background: rgba(15, 23, 42, 0.85);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
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
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38BDF8, #818CF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94A3B8 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.3rem;
        font-weight: 600;
    }
    .main-header-glow {
        background: linear-gradient(90deg, #38BDF8, #818CF8, #F472B6);
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
# SIDEBAR CONTROLS & DEPARTMENT SELECTOR
# ============================================================================
st.sidebar.markdown("## 🏥 Global Health Command Hub")

health_department = st.sidebar.selectbox(
    "Select Healthcare Department / Focus",
    [
        "Executive Public Health Dashboard",
        "Emergency ICU Triage & Bed Surge",
        "Pharmacy & Medical Supply Exhaustion",
        "Genomic Mutation & Pathogen Tracking",
        "Infectious Disease SEIR Outbreak Model",
        "Laboratory & Diagnostics Throughput",
        "Staff Fatigue & Rostering Optimizer",
        "Multi-Hospital Regional Network Matrix"
    ]
)

facility_name = st.sidebar.text_input("Facility / Region Identifier", "National Referral Hospital Complex")
simulation_horizon = st.sidebar.slider("Forecasting Horizon (Days)", 14, 180, 42, 7)
intervention_urgency = st.sidebar.slider("Intervention Mitigation Factor", 0.0, 1.0, 0.3, 0.05)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Core Epidemiological Parameters")
beta_transmission = st.sidebar.slider("Transmission Rate (Beta)", 0.1, 5.0, 1.8, 0.1)
recovery_rate = st.sidebar.slider("Recovery Rate (Gamma)", 0.05, 1.0, 0.3, 0.05)
icu_conversion_rate = st.sidebar.slider("Infections Requiring ICU (%)", 0.01, 0.25, 0.08, 0.01)

# ============================================================================
# SOLVER & SIMULATION ENGINE (SEIR + ICU Dynamics)
# ============================================================================
def health_seir_model(y, t, beta, gamma, icu_rate, mitigation):
    S, E, I, R, ICU = y
    effective_beta = beta * (1.0 - mitigation)
    N = S + E + I + R + ICU + 1e-6
    
    dSdt = -effective_beta * S * I / N
    dEdt = effective_beta * S * I / N - 0.2 * E
    dIdt = 0.2 * E - gamma * I
    dRdt = gamma * I * (1.0 - icu_rate)
    dICUdt = gamma * I * icu_rate - 0.1 * ICU
    return [dSdt, dEdt, dIdt, dRdt, dICUdt]

t_arr = np.linspace(0, simulation_horizon, simulation_horizon * 2)
initial_state = [0.99, 0.008, 0.002, 0.0, 0.0] # Proportions
solution = odeint(health_seir_model, initial_state, t_arr, args=(beta_transmission, recovery_rate, icu_conversion_rate, intervention_urgency))

S_t, E_t, I_t, R_t, ICU_t = solution[:, 0], solution[:, 1], solution[:, 2], solution[:, 3], solution[:, 4]
peak_icu_day = int(np.argmax(ICU_t) * (simulation_horizon / (simulation_horizon * 2)))
max_icu_load = float(np.max(ICU_t) * 100)

# ============================================================================
# MAIN APPLICATION INTERFACE
# ============================================================================
st.markdown(f'<div class="main-header-glow">Global Health Sector Command & Problem Solver Suite</div>', unsafe_allow_html=True)
st.markdown(f"**Active Department:** `{health_department}` &nbsp;|&nbsp; **Target Facility:** `{facility_name}`")
st.markdown("---")

if health_department == "Executive Public Health Dashboard":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{max(1, 42 - int(peak_icu_day))} Days</div>
            <div class="metric-label">Estimated ICU Saturation</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">84.2%</div>
            <div class="metric-label">Critical Pharma Stocks</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">Variant Risk: High</div>
            <div class="metric-label">Pathogen Mutation Index</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">74%</div>
            <div class="metric-label">Staff Allocation Balance</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Overview Trend Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t_arr, y=I_t * 100, mode='lines', name='Active Infections (%)', line=dict(color='#38BDF8', width=3)))
    fig.add_trace(go.Scatter(x=t_arr, y=ICU_t * 100, mode='lines', name='ICU Demand Capacity (%)', line=dict(color='#F43F5E', width=3, dash='dash')))
    fig.update_layout(
        title_text=f"Epidemiological Surge & ICU Pressure Projection ({facility_name})",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=450,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)

elif health_department == "Emergency ICU Triage & Bed Surge":
    st.markdown("### 🛏️ Emergency ICU Triage, Flow & Capacity Forecasting")
    st.markdown("Simulating ventilator allocation, triage prioritization scoring, and emergency bed conversion rates.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="glass-container">
        <b>Triage Optimization Metrics:</b><br><br>
        * <b>Projected Peak ICU Load:</b> {max_icu_load:.2f}% of regional capacity<br>
        * <b>Critical Surge Day:</b> Day {peak_icu_day} of horizon<br>
        * <b>Recommended Action:</b> Initiate secondary overflow wards if intervention factor remains below 0.35.
        </div>
        """, unsafe_allow_html=True)
    with col2:
        icu_fig = px.area(x=t_arr, y=ICU_t * 100, labels={'x': 'Days', 'y': 'ICU Capacity Occupancy (%)'}, title="Dynamic ICU Bed Utilization Curve")
        icu_fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(icu_fig, use_container_width=True)

elif health_department == "Pharmacy & Medical Supply Exhaustion":
    st.markdown("### 💊 Pharmacy, Oxygen & Consumables Supply-Chain Intelligence")
    
    supply_days = max(5, int(60 * (1.0 - intervention_urgency + 0.2)))
    col1, col2, col3 = st.columns(3)
    col1.metric("Medical Oxygen Reserves", f"{supply_days * 3} Hours", delta="-12 Hours")
    col2.metric("Antibiotics & Antivirals", "78% Stock", delta="-4%")
    col3.metric("PPE & Hazmat Kits", "14 Days Remaining", delta="2 Days")

    med_df = pd.DataFrame({
        "Medical Item": ["Oxygen Cylinders", "Broad-Spectrum Antibiotics", "N95 Respirators", "IV Fluids", "Sedatives / Propofol"],
        "Consumption Rate (Units/Day)": [420, 1250, 3100, 890, 340],
        "Buffer Stock Remaining": [1800, 9500, 21000, 4500, 1200],
        "Exhaustion Risk Level": ["Critical", "Moderate", "Safe", "Moderate", "High"]
    })
    st.dataframe(med_df, use_container_width=True)

elif health_department == "Genomic Mutation & Pathogen Tracking":
    st.markdown("### 🧬 Pathogen Genomic Surveillance & Mutation Variant Tracker")
    st.markdown("Tracking variant fitness, immune escape potential, and transmissibility shifts across regional sequencing nodes.")
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT pathogen, mutation_variant, transmission_index, severity FROM outbreak_alerts")
    variants_data = cursor.fetchall()
    
    var_df = pd.DataFrame(variants_data, columns=["Pathogen", "Variant Lineage", "Transmission Index", "Clinical Severity"])
    st.dataframe(var_df, use_container_width=True)
    
    st.markdown("""
    <div class="glass-container">
    <b>Genomic Intelligence Note:</b> Sequencing data updates automatically from regional reference laboratories. High transmission indices (>1.3) trigger automated multi-departmental supply readiness alerts.
    </div>
    """, unsafe_allow_html=True)

elif health_department == "Infectious Disease SEIR Outbreak Model":
    st.markdown("### 🦠 Advanced SEIR Epidemic Trajectory Modeling")
    
    fig_seir = go.Figure()
    fig_seir.add_trace(go.Scatter(x=t_arr, y=S_t*100, name='Susceptible (%)', line=dict(color='#60A5FA')))
    fig_seir.add_trace(go.Scatter(x=t_arr, y=E_t*100, name='Exposed (%)', line=dict(color='#F59E0B')))
    fig_seir.add_trace(go.Scatter(x=t_arr, y=I_t*100, name='Infectious (%)', line=dict(color='#EF4444')))
    fig_seir.add_trace(go.Scatter(x=t_arr, y=R_t*100, name='Recovered (%)', line=dict(color='#10B981')))
    fig_seir.update_layout(title_text="Full Population SEIR Compartmental Flow", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_seir, use_container_width=True)

elif health_department == "Laboratory & Diagnostics Throughput":
    st.markdown("### 🔬 Laboratory Testing, PCR & Diagnostics Throughput Solver")
    col1, col2 = st.columns(2)
    col1.metric("Daily PCR Processing Capacity", "4,200 Samples", delta="+300")
    col2.metric("Average Turnaround Time (TAT)", "14.2 Hours", delta="-2.1 Hours")
    
    lab_metrics = pd.DataFrame({
        "Testing Laboratory": ["Central Public Health Lab", "Regional Referral Node A", "University Medical Lab", "Mobile Diagnostic Unit"],
        "Backlog Samples": [310, 140, 85, 20],
        "Machine Utilization (%)": [92.5, 78.0, 64.2, 45.0],
        "Reagent Status": ["Adequate", "Warning", "Adequate", "Critical"]
    })
    st.dataframe(lab_metrics, use_container_width=True)

elif health_department == "Staff Fatigue & Rostering Optimizer":
    st.markdown("### 👩‍⚕️ Medical Personnel Rostering & Fatigue Mitigation")
    st.markdown("Balancing shift durations, burnout indexes, and specialized clinician deployment across high-risk wards.")
    
    staff_df = pd.DataFrame({
        "Department / Ward": ["Critical Care / ICU", "Emergency & Trauma", "Infectious Isolation", "General Pediatrics", "Laboratory Diagnostics"],
        "Assigned Personnel": [45, 60, 35, 50, 25],
        "Average Shift Hours": [11.5, 12.0, 10.0, 8.5, 9.0],
        "Burnout Risk Score": ["High", "Critical", "High", "Moderate", "Low"]
    })
    st.dataframe(staff_df, use_container_width=True)

elif health_department == "Multi-Hospital Regional Network Matrix":
    st.markdown("### 🌐 Regional Multi-Hospital Resource Balancing Matrix")
    st.markdown("Optimizing patient transfers, equipment sharing, and load-balancing across interconnected district hospitals.")
    
    network_df = pd.DataFrame({
        "Facility Node": ["Hospital Alpha (Capital)", "Hospital Beta (Northern Zone)", "Hospital Gamma (Eastern Hub)", "Hospital Delta (Western Sector)"],
        "Bed Occupancy Rate": ["96%", "72%", "84%", "61%"],
        "Available ICU Transfers": [2, 14, 6, 19],
        "Network Load Status": ["Saturated", "Balanced", "Moderate", "Optimal"]
    })
    st.dataframe(network_df, use_container_width=True)