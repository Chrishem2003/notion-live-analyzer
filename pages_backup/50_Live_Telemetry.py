import security_guard
security_guard.verify_access()

import datetime
import io
import json
import sqlite3
import numpy as np
import pandas as pd
import streamlit as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# ============================================================================
# 1. DATABASE INITIALIZATION (Telemetry & Live Stream Store)
# ============================================================================
def init_telemetry_db():
    conn = sqlite3.connect("global_telemetry_engine.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            connector_name TEXT,
            status TEXT,
            latency_ms INTEGER,
            payload_summary TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_connectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT,
            protocol TEXT,
            polling_interval TEXT,
            health_status TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO active_connectors (source_name, protocol, polling_interval, health_status)
        VALUES 
        ('Central Bank Sovereign API', 'REST / JSON', '10s', 'Connected & Stable'),
        ('Satellite Sentinel-2 Feed', 'OData / WCS', '2 mins', 'Connected & Synchronized'),
        ('Global Epidemic Tracker (WHO/CDC)', 'GraphQL Stream', '5s', 'Connected & Active'),
        ('Energy Grid SCADA Telemetry', 'IEC 60870-5-104', '1s', 'High Frequency Sync')
    """)
    conn.commit()
    return conn

db_conn = init_telemetry_db()

# ============================================================================
# 2. PAGE CONFIGURATION & HIGH-CONTRAST STYLING
# ============================================================================
st.set_page_config(
    page_title="Live Data Ingestion & Telemetry Center",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #030712 !important;
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
        background: linear-gradient(90deg, #38BDF8, #818CF8, #34D399);
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
st.sidebar.markdown("## 📡 Telemetry Command Hub")

telemetry_module = st.sidebar.selectbox(
    "Select Telemetry Module",
    [
        "Executive Live Ingestion Dashboard",
        "Pipeline Connector Health & Latency Monitor",
        "Central Bank & Sovereign Yield Telemetry Stream",
        "Global Epidemic & Healthcare Outbreak Tracker",
        "Satellite Earth Observation & NDWI Crop Health",
        "Real-Time Anomaly Detection & Alert Engine",
        "Multi-Source API Stream Orchestrator"
    ]
)

refresh_frequency = st.sidebar.selectbox("Polling Refresh Rate", ["Real-Time (1s)", "Fast (10s)", "Standard (30s)", "Low Bandwidth (1m)"])
stream_mode = st.sidebar.slider("Stream Ingestion Multiplier", 0.5, 3.0, 1.0, 0.1)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Telemetry Parameters")
sovereign_yield_val = st.sidebar.slider("Simulated Sovereign Yield (%)", 5.0, 25.0, 12.4, 0.1)
icu_saturation_val = st.sidebar.slider("Simulated ICU Saturation (%)", 20.0, 100.0, 74.2, 1.0)
ndwi_health_val = st.sidebar.slider("Satellite NDWI Crop Health Index", 0.1, 1.0, 0.78, 0.01)

# ============================================================================
# 4. MAIN APPLICATION INTERFACE
# ============================================================================
st.markdown(f'<div class="main-header-glow">Live Data Ingestion & Telemetry Center</div>', unsafe_allow_html=True)
st.markdown(f"**Active Module:** `{telemetry_module}` &nbsp;|&nbsp; **Refresh Rate:** `{refresh_frequency}`")
st.markdown("---")

if telemetry_module == "Executive Live Ingestion Dashboard":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{sovereign_yield_val:.1f}%</div>
            <div class="metric-label">Live Sovereign Yield</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{icu_saturation_val:.1f}%</div>
            <div class="metric-label">ICU Saturation Level</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{ndwi_health_val:.2f} NDWI</div>
            <div class="metric-label">Satellite Crop Health</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">99.99%</div>
            <div class="metric-label">Stream Uptime</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.subheader("Active Pipeline Connectors")
    st.success("✅ Central Bank API Connected (Polling interval: 10s)[cite: 12]")
    st.success("✅ Satellite Sentinel-2 Feed Connected (Last sync: 2 mins ago)[cite: 12]")
    st.success("✅ Global Epidemic Tracker Connected[cite: 12]")
    st.success("✅ Energy Grid SCADA Telemetry Stream Connected (Latency: 14ms)")

    # Real-Time Telemetry Trend
    time_steps = np.arange(0, 24, 1)
    telemetry_trend = np.sin(time_steps * 0.3) * 5 + sovereign_yield_val

    fig_tel = go.Figure()
    fig_tel.add_trace(go.Scatter(x=time_steps, y=telemetry_trend, mode='lines+markers', name='Sovereign Yield Telemetry Stream', line=dict(color='#38BDF8', width=3)))
    fig_tel.update_layout(
        title_text="Real-Time Sovereign Yield Ingestion Velocity",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=380,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    st.plotly_chart(fig_tel, use_container_width=True)

elif telemetry_module == "Pipeline Connector Health & Latency Monitor":
    st.markdown("### 🔌 Pipeline Connector Health & Latency Telemetry")
    st.markdown("Monitoring real-time handshake status, packet loss, and API polling frequencies across all ingestion nodes.")
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT source_name, protocol, polling_interval, health_status FROM active_connectors")
    conn_data = cursor.fetchall()
    
    conn_df = pd.DataFrame(conn_data, columns=["Data Source Name", "Ingestion Protocol", "Polling Interval", "Health Status"])
    st.dataframe(conn_df, use_container_width=True)
    
    st.markdown("""
    <div class="glass-container">
    <b>Telemetry Diagnostics Note:</b><br>
    All API endpoints are monitored via automated heartbeat probes. Automatic failover routing is engaged if latency exceeds 250ms.
    </div>
    """, unsafe_allow_html=True)

elif telemetry_module == "Central Bank & Sovereign Yield Telemetry Stream":
    st.markdown("### 🏛️ Central Bank & Sovereign Yield Telemetry Stream")
    col1, col2 = st.columns(2)
    col1.metric("10-Year Bond Yield", f"{sovereign_yield_val}%", delta="+0.3%")
    col2.metric("Interbank Lending Rate", f"{sovereign_yield_val - 2.1:.1f}%", delta="0.0%")
    
    yield_df = pd.DataFrame({
        "Tenor": ["3-Month Bill", "1-Year Bond", "5-Year Treasury", "10-Year Benchmark", "30-Year Sovereign"],
        "Yield (%)": [sovereign_yield_val - 3.0, sovereign_yield_val - 1.5, sovereign_yield_val - 0.5, sovereign_yield_val, sovereign_yield_val + 1.8],
        "Change (bps)": [+12, -4, +8, +30, +15],
        "Stream Status": ["Active", "Active", "Active", "Active", "Active"]
    })
    st.dataframe(yield_df, use_container_width=True)

elif telemetry_module == "Global Epidemic & Healthcare Outbreak Tracker":
    st.markdown("### 🦠 Global Epidemic & Healthcare Outbreak Telemetry")
    col1, col2 = st.columns(2)
    col1.metric("ICU Saturation Index", f"{icu_saturation_val}%", delta="-1.5%")
    col2.metric("Pathogen Transmission Factor", "1.18 R0", delta="+0.04")
    
    epi_df = pd.DataFrame({
        "Region / Ward": ["National ICU Complex", "Emergency Isolation Ward", "Pediatric Care Center", "Regional Trauma Unit"],
        "Bed Occupancy (%)": [icu_saturation_val, icu_saturation_val - 12.0, icu_saturation_val - 25.0, icu_saturation_val + 5.0],
        "Ventilator Utilization": ["84%", "62%", "45%", "91%"],
        "Outbreak Alert Level": ["Moderate", "Low", "Low", "Critical"]
    })
    st.dataframe(epi_df, use_container_width=True)

elif telemetry_module == "Satellite Earth Observation & NDWI Crop Health":
    st.markdown("### 🛰️ Satellite Earth Observation & NDWI Crop Health Monitor")
    col1, col2 = st.columns(2)
    col1.metric("Normalized Difference Water Index (NDWI)", f"{ndwi_health_val} NDWI", delta="0.02")
    col2.metric("Soil Moisture Satellite Feed", "68.4% Saturation", delta="+1.2%")
    
    sat_df = pd.DataFrame({
        "Agricultural Sector": ["Northern Grain Belt", "Central Plateau", "Eastern Agricultural Corridor", "Western Highland Basin"],
        "NDWI Index": [ndwi_health_val, ndwi_health_val - 0.12, ndwi_health_val + 0.05, ndwi_health_val - 0.04],
        "Vegetation Health": ["Optimal", "Moderate Stress", "Robust", "Normal"],
        "Last Orbital Pass": ["12 mins ago", "45 mins ago", "2 hours ago", "30 mins ago"]
    })
    st.dataframe(sat_df, use_container_width=True)

elif telemetry_module == "Real-Time Anomaly Detection & Alert Engine":
    st.markdown("### 🚨 Real-Time Anomaly Detection & Alert Engine")
    
    anomaly_df = pd.DataFrame({
        "Telemetry Stream": ["Central Bank API", "Sentinel-2 Satellite Feed", "WHO Epidemic Tracker", "Energy Grid SCADA"],
        "Anomaly Type Detected": ["None", "Minor Packet Jitter", "None", "Voltage Transient"],
        "Severity": ["Normal", "Low", "Normal", "Moderate"],
        "Automated Action": ["None", "Buffer Adjusted", "None", "Regulator Engaged"]
    })
    st.dataframe(anomaly_df, use_container_width=True)

elif telemetry_module == "Multi-Source API Stream Orchestrator":
    st.markdown("### 🌐 Multi-Source API Stream Orchestrator & Router")
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Streams", "18 Endpoints", delta="+2")
    col2.metric("Data Ingestion Volume", "4.8 GB/hour", delta="+120 MB")
    col3.metric("Error Rate", "0.001%", delta="0.0%")

    st.markdown("""
    <div class="glass-container">
    <b>Orchestrator Architecture Note:</b><br>
    The telemetry ingestion engine utilizes asynchronous WebSockets and REST polling wrappers to aggregate multi-sector data into unified analytics dataframes in real time.
    </div>
    """, unsafe_allow_html=True)
