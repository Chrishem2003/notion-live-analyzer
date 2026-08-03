import security_guard
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
# DATABASE INITIALIZATION (Agri-Food Command Store)
# ============================================================================
def init_agri_db():
    conn = sqlite3.connect("global_agri_security.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_security_simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            region TEXT,
            reserve_days INTEGER,
            vulnerability_score REAL,
            metrics_payload TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intervention_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT,
            hazard_type TEXT,
            urgency_level TEXT,
            recommended_action TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO intervention_logs (region, hazard_type, urgency_level, recommended_action)
        VALUES 
        ('East Africa Corridor', 'Border Transit Delay (36h)', 'High', 'Deploy expedited customs clearance lanes & cold-chain priority.'),
        ('Northern Grain Belt', 'Prolonged Dry Spell', 'Critical', 'Initiate emergency groundwater irrigation and grain release.'),
        ('Central Agricultural Hub', 'Fertilizer Price Pass-Through', 'Moderate', 'Activate farmer subsidy vouchers and localized distribution.')
    """)
    conn.commit()
    return conn

db_conn = init_agri_db()

# ============================================================================
# PAGE CONFIG & PREMIUM HIGH-CONTRAST STYLING
# ============================================================================
st.set_page_config(
    page_title="Global Agriculture & Food Security Command Suite",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #061a14 !important;
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
        background: linear-gradient(135deg, #022c22 0%, #064e3b 50%, #022c22 100%);
        background-attachment: fixed;
    }
    .glass-container {
        background: rgba(6, 78, 59, 0.75);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.6);
        color: #F8FAFC !important;
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(6, 95, 70, 0.9) 0%, rgba(2, 44, 34, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #34D399, #6EE7B7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #A7F3D0 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.3rem;
        font-weight: 600;
    }
    .main-header-glow {
        background: linear-gradient(90deg, #34D399, #6EE7B7, #FBBF24);
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
# SIDEBAR CONTROLS & MODULE SELECTOR
# ============================================================================
st.sidebar.markdown("## 🌾 Agri-Food Command Hub")

agri_module = st.sidebar.selectbox(
    "Select Agricultural & Food Module",
    [
        "Executive Food Security Dashboard",
        "National Grain Reserve & Depletion Timer",
        "Climate Drought & Crop Yield Forecasting",
        "Supply-Chain Bottleneck & Border Logistics",
        "Fertilizer Price Pass-Through & Subsidy Impact",
        "Pest Outbreak & Crop Disease Surveillance",
        "Global Food Trade & Regional Resilience Matrix"
    ]
)

target_region = st.sidebar.selectbox("Target Region / Country", [
    "East Africa Regional Hub", "Uganda Agricultural Zone", "Kenya Food Security Sector", 
    "Horn of Africa Corridor", "West Africa Grain Network", "Global Aggregate"
])

forecasting_weeks = st.sidebar.slider("Forecasting Horizon (Weeks)", 4, 52, 24, 4)
climate_stress_factor = st.sidebar.slider("Climate Drought Stress Multiplier", 0.0, 2.0, 1.0, 0.1)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Core Agricultural Parameters")
consumption_rate = st.sidebar.slider("Daily Grain Consumption (Tons/Day)", 1000, 25000, 8500, 500)
initial_reserve_tons = st.sidebar.slider("Initial Grain Stockpile (Thousand Tons)", 500, 5000, 1840, 50)
fertilizer_inflation = st.sidebar.slider("Fertilizer Price Increase (%)", 0.0, 50.0, 8.4, 0.5)

# ============================================================================
# SIMULATION ENGINE (Grain Depletion & Food Security ODE)
# ============================================================================
def food_security_model(y, t, consumption, stress):
    Stock, Vulnerability, PriceIndex = y
    # Stock: Grain Reserves, Vulnerability: Food Insecurity Index, PriceIndex: Food Price Index
    dStockdt = -consumption * 0.001 - (stress * 12.0)
    dVulnDt = 0.05 * stress + 0.01 * (1.0 / (Stock + 1.0))
    dPricedt = 0.4 * fertilizer_inflation + 0.2 * stress - 0.1 * PriceIndex
    return [dStockdt, dVulnDt, dPricedt]

t_weeks = np.linspace(0, forecasting_weeks, forecasting_weeks * 2)
initial_state = [initial_reserve_tons / 1000.0, 0.25, 100.0]
simulation_solution = odeint(food_security_model, initial_state, t_weeks, args=(consumption_rate, climate_stress_factor))

stock_traj, vuln_traj, price_traj = simulation_solution[:, 0], simulation_solution[:, 1], simulation_solution[:, 2]
estimated_buffer_days = int((stock_traj[-1] * 1000000) / max(1, consumption_rate))

# ============================================================================
# MAIN APPLICATION INTERFACE
# ============================================================================
st.markdown(f'<div class="main-header-glow">Global Agriculture & Food Security Command Suite</div>', unsafe_allow_html=True)
st.markdown(f"**Active Module:** `{agri_module}` &nbsp;|&nbsp; **Target Zone:** `{target_region}`")
st.markdown("---")

if agri_module == "Executive Food Security Dashboard":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{max(14, estimated_buffer_days)} Days</div>
            <div class="metric-label">National Grain Reserve Buffer</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{fertilizer_inflation:.1f}%</div>
            <div class="metric-label">Fertilizer Cost Burden</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">Risk: Moderate</div>
            <div class="metric-label">Drought Vulnerability Index</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">36-Hour Delay</div>
            <div class="metric-label">Border Transit Bottleneck</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    col_alert1, col_alert2 = st.columns(2)
    with col_alert1:
        st.error("🔍 **Supply Chain Alert:** Regional border crossing experiencing 36-hour transit delays impacting perishable produce and grain distribution.")
    with col_alert2:
        st.warning("⚠️ **Drought Warning:** Extended dry spells predicted across northern agricultural belts; early irrigation release recommended.")

    fig_exec = go.Figure()
    fig_exec.add_trace(go.Scatter(x=t_weeks, y=stock_traj * 1000, mode='lines', name='Grain Reserve Stockpile (Thousand Tons)', line=dict(color='#34D399', width=3)))
    fig_exec.add_trace(go.Scatter(x=t_weeks, y=vuln_traj * 100, mode='lines', name='Population Vulnerability Index (%)', line=dict(color='#FBBF24', width=3, dash='dash')))
    fig_exec.update_layout(
        title_text=f"Grain Reserve Depletion & Vulnerability Trajectory ({target_region})",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=450,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    st.plotly_chart(fig_exec, use_container_width=True)

elif agri_module == "National Grain Reserve & Depletion Timer":
    st.markdown("### 🏛️ National Grain Reserve & Strategic Depletion Timer")
    st.markdown("Simulating national storage capacities, daily consumption rates, and automated emergency release thresholds.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="glass-container">
        <b>Reserve Depletion Diagnostics:</b><br><br>
        * <b>Current Stockpile:</b> {initial_reserve_tons} Thousand Tons<br>
        * <b>Estimated Buffer Duration:</b> {max(14, estimated_buffer_days)} Days<br>
        * <b>Recommended Intervention:</b> {"Trigger emergency grain release if buffer falls below 90 days." if estimated_buffer_days < 90 else "Reserves are stable within optimal parameters."}
        </div>
        """, unsafe_allow_html=True)
    with col2:
        grain_fig = px.line(x=t_weeks, y=stock_traj * 1000, labels={'x': 'Weeks', 'y': 'Reserve Stock (Thousand Tons)'}, title="Grain Reserve Burn-Down Curve")
        grain_fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=320, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(grain_fig, use_container_width=True)

elif agri_module == "Climate Drought & Crop Yield Forecasting":
    st.markdown("### ☀️ Climate Drought Risk & Crop Yield Forecasting")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Soil Moisture Index", f"{max(15, 65 - int(climate_stress_factor * 20))}% Capacity", delta="-4.2%")
    col2.metric("Precipitation Anomaly", "-24% Below Normal", delta="-6%")
    col3.metric("Projected Yield Impact", f"-{int(climate_stress_factor * 12)}% Harvest Deficit", delta="-2.5%")

    drought_df = pd.DataFrame({
        "Agricultural Zone": ["Northern Grain Belt", "Central Plateau", "Eastern Lowlands", "Western Highland Valleys"],
        "Drought Risk Level": ["Critical", "Moderate", "High", "Low"],
        "Soil Saturation (%)": [28.5, 52.0, 38.2, 74.5],
        "Recommended Action": ["Groundwater Irrigation", "Monitor Crops", "Drought-Resistant Seeds", "Normal Operations"]
    })
    st.dataframe(drought_df, use_container_width=True)

elif agri_module == "Supply-Chain Bottleneck & Border Logistics":
    st.markdown("### 🚚 Supply-Chain Bottleneck & Border Crossing Mapping")
    
    col1, col2 = st.columns(2)
    col1.metric("Average Border Transit Delay", "36 Hours", delta="+12 Hours")
    col2.metric("Cold-Chain Integrity Score", "82% Compliant", delta="-5%")

    cursor = db_conn.cursor()
    cursor.execute("SELECT region, hazard_type, urgency_level, recommended_action FROM intervention_logs")
    logs_data = cursor.fetchall()
    
    log_df = pd.DataFrame(logs_data, columns=["Corridor / Region", "Hazard Type", "Urgency Level", "Required Intervention"])
    st.dataframe(log_df, use_container_width=True)

elif agri_module == "Fertilizer Price Pass-Through & Subsidy Impact":
    st.markdown("### 🧪 Fertilizer Price Pass-Through & Input Cost Optimizer")
    col1, col2 = st.columns(2)
    col1.metric("Fertilizer Price Index", f"{100 + fertilizer_inflation:.1f} Base Pts", delta=f"+{fertilizer_inflation:.1f}%")
    col2.metric("Farmer Adoption Rate", "68.4%", delta="-5.2%")
    
    fert_df = pd.DataFrame({
        "Fertilizer Type": ["Urea (Nitrogen)", "DAP (Phosphates)", "NPK Compound", "Organic Composts"],
        "Market Cost ($/Ton)", [640, 720, 680, 210],
        "Subsidy Voucher Value ($)", [150, 180, 160, 90],
        "Accessibility Status": ["Strained", "Critical", "Moderate", "High Availability"]
    })
    st.dataframe(fert_df, use_container_width=True)

elif agri_module == "Pest Outbreak & Crop Disease Surveillance":
    st.markdown("### 🐛 Pest Outbreak & Crop Disease Early Warning System")
    st.markdown("Tracking migratory locust swarms, fall armyworm infestations, and fungal blast epidemics.")
    
    pest_df = pd.DataFrame({
        "Pest / Pathogen Threat": ["Fall Armyworm", "Desert Locust Swarm", "Wheat Stem Rust", "Cassava Mosaic Virus"],
        "Affected Acreage (Hectares)": [45000, 120000, 8500, 15000],
        "Transmission Velocity": ["High", "Moderate", "Critical", "Stable"],
        "Control Measures Deployed": ["Targeted Bio-Pesticides", "Aerial Monitoring", "Resistant Cultivars", "Quarantine"]
    })
    st.dataframe(pest_df, use_container_width=True)

elif agri_module == "Global Food Trade & Regional Resilience Matrix":
    st.markdown("### 🌐 Global Food Trade & Regional Resilience Matrix")
    st.markdown("Analyzing cross-border import dependency, export restrictions, and regional food security resilience.")
    
    resilience_df = pd.DataFrame({
        "Regional Economic Bloc": ["East African Community (EAC)", "COMESA Trade Area", "SADC Food Security Hub", "ECOWAS Grain Reserve"],
        "Import Dependency Ratio": ["32%", "45%", "28%", "39%"],
        "Resilience Score": ["Moderate", "Vulnerable", "Robust", "Stable"],
        "Strategic Priority": ["Corridor Harmonization", "Buffer Expansion", "Logistics Upgrade", "Input Subsidies"]
    })
    st.dataframe(resilience_df, use_container_width=True)

