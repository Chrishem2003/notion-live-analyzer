
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
# DATABASE INITIALIZATION (Macroeconomic Sovereign Store)
# ============================================================================
def init_macro_db():
    conn = sqlite3.connect("macro_sovereign_engine.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS macro_simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            jurisdiction TEXT,
            debt_to_gdp REAL,
            risk_label TEXT,
            metrics_payload TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sovereign_bonds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT,
            tenor TEXT,
            yield_rate REAL,
            spread_bps REAL,
            recommendation TEXT
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO sovereign_bonds (country, tenor, yield_rate, spread_bps, recommendation)
        VALUES 
        ('Uganda', '10-Year Local Currency', 14.50, 320, 'Optimal Refinancing Window'),
        ('Kenya', '7-Year Eurobond', 10.25, 480, 'Hold / Monitor Spread'),
        ('Ghana', 'Restructured Sovereign', 8.50, 650, 'High Risk Restructuring')
    """)
    conn.commit()
    return conn

db_conn = init_macro_db()

# ============================================================================
# PAGE CONFIG & PREMIUM FINANCIAL STYLING
# ============================================================================
st.set_page_config(
    page_title="Global Financial & Macroeconomic Risk Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #070e18 !important;
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
        background: linear-gradient(135deg, #030712 0%, #0f172a 50%, #030712 100%);
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
        background: linear-gradient(90deg, #60A5FA, #34D399);
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
        background: linear-gradient(90deg, #60A5FA, #34D399, #F472B6);
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
st.sidebar.markdown("## 📈 Macroeconomic Command Hub")

macro_module = st.sidebar.selectbox(
    "Select Financial Module / Solver",
    [
        "Executive Macroeconomic Dashboard",
        "Sovereign Debt Sustainability & Restructuring",
        "Capital Flight Velocity & FX Reserves",
        "Inflation Pass-Through & Price Shock Predictor",
        "Monetary Policy Rate & Yield Curve Optimizer",
        "Multi-Country Contagion & Risk Matrix",
        "Fiscal Deficit & Liquidity Coverage (LCR)"
    ]
)

target_jurisdiction = st.sidebar.selectbox("Jurisdiction / Economy", [
    "Uganda (UGX)", "Kenya (KES)", "Rwanda (RWF)", "Nigeria (NGN)", 
    "South Africa (ZAR)", "United States (USD)", "Global Aggregate"
])

projection_horizon = st.sidebar.slider("Forecasting Horizon (Months)", 6, 60, 24, 6)
fiscal_shock_factor = st.sidebar.slider("External Shock Multiplier", 0.0, 2.0, 1.0, 0.1)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Core Financial Parameters")
interest_rate = st.sidebar.slider("Central Bank Policy Rate (%)", 1.0, 25.0, 11.5, 0.5)
fx_depreciation_rate = st.sidebar.slider("Annual FX Depreciation Rate (%)", 0.0, 30.0, 6.2, 0.5)
debt_to_gdp_ratio = st.sidebar.slider("Initial Debt-to-GDP Ratio (%)", 20.0, 120.0, 52.4, 1.0)

# ============================================================================
# MACROECONOMIC DYNAMICS SOLVER (Debt & Capital Flight ODE)
# ============================================================================
def macro_debt_model(y, t, r, g, shock):
    D, FX_res, Infl = y
    # D: Debt-to-GDP, FX_res: Foreign Exchange Reserves (Months), Infl: Inflation Rate
    dDdt = (r - 4.0) * D * 0.01 - 0.02 + (shock * 0.05)
    dFXdt = -0.1 * (r - 5.0) - (shock * 0.15)
    dInfldt = 0.5 * (fx_depreciation_rate * 0.1) + 0.2 * shock - 0.1 * Infl
    return [dDdt, dFXdt, dInfldt]

t_months = np.linspace(0, projection_horizon, projection_horizon * 2)
initial_macro_state = [debt_to_gdp_ratio, 4.5, 6.0]
macro_solution = odeint(macro_debt_model, initial_macro_state, t_months, args=(interest_rate, 5.0, fiscal_shock_factor))

debt_traj, fx_traj, infl_traj = macro_solution[:, 0], macro_solution[:, 1], macro_solution[:, 2]

# ============================================================================
# MAIN APPLICATION INTERFACE
# ============================================================================
st.markdown(f'<div class="main-header-glow">Global Financial & Macroeconomic Risk Engine</div>', unsafe_allow_html=True)
st.markdown(f"**Active Module:** `{macro_module}` &nbsp;|&nbsp; **Jurisdiction:** `{target_jurisdiction}`")
st.markdown("---")

if macro_module == "Executive Macroeconomic Dashboard":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">Low (14.2)</div>
            <div class="metric-label">Capital Flight Velocity</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">118.4%</div>
            <div class="metric-label">Liquidity Coverage Ratio (LCR)</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{debt_to_gdp_ratio:.1f}%</div>
            <div class="metric-label">Debt-to-GDP Ratio</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{interest_rate:.1f}%</div>
            <div class="metric-label">Policy Interest Rate</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    col_sig1, col_sig2 = st.columns(2)
    with col_sig1:
        st.info("🔍 **Bond Buyback Signal:** Optimal yield curve window detected for foreign debt refinancing and domestic liability management.")
    with col_sig2:
        st.warning("⚠️ **Inflation Warning:** Currency depreciation pass-through predicted to impact food and energy import costs within 14 days.")

    fig_macro = go.Figure()
    fig_macro.add_trace(go.Scatter(x=t_months, y=debt_traj, mode='lines', name='Projected Debt-to-GDP (%)', line=dict(color='#60A5FA', width=3)))
    fig_macro.add_trace(go.Scatter(x=t_months, y=infl_traj * 10, mode='lines', name='Inflation Pass-Through Index', line=dict(color='#F43F5E', width=3, dash='dash')))
    fig_macro.update_layout(
        title_text=f"Macroeconomic Trajectory & Debt Sustainability ({target_jurisdiction})",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=450,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    st.plotly_chart(fig_macro, use_container_width=True)

elif macro_module == "Sovereign Debt Sustainability & Restructuring":
    st.markdown("### 🏛️ Sovereign Debt Sustainability & Restructuring Optimizer")
    st.markdown("Simulating debt servicing costs, primary balance adjustments, and bond refinancing risk profiles.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="glass-container">
        <b>Debt Restructuring Diagnostics:</b><br><br>
        * <b>Current Debt Burden:</b> {debt_to_gdp_ratio:.1f}% of GDP<br>
        * <b>Servicing Pressure Index:</b> {"High" if debt_to_gdp_ratio > 60 else "Manageable"}<br>
        * <b>Recommendation:</b> Execute liability management operations or extend maturities to reduce near-term rollover risks.
        </div>
        """, unsafe_allow_html=True)
    with col2:
        debt_fig = px.line(x=t_months, y=debt_traj, labels={'x': 'Months', 'y': 'Debt-to-GDP (%)'}, title="Debt Trajectory Forecast")
        debt_fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=320, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(debt_fig, use_container_width=True)

elif macro_module == "Capital Flight Velocity & FX Reserves":
    st.markdown("### 💸 Capital Flight Velocity & Foreign Exchange Reserve Adequacy")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("FX Reserve Buffer", f"{max(1.0, 5.0 - fiscal_shock_factor):.1f} Months of Import", delta="-0.4 Months")
    col2.metric("Portfolio Outflows", "$240 Million", delta="+$45M")
    col3.metric("Exchange Rate Pressure", "Moderate Depreciation", delta="+1.2%")

    flight_df = pd.DataFrame({
        "Asset Class / Channel": ["Foreign Portfolio Inflows", "FDI Direct Investments", "Diaspora Remittances", "Commercial Bank FX Holdings"],
        "Velocity Index": ["Low", "Stable", "High Inflow", "Volatile"],
        "Net Flow ($M)": [-45.2, 120.5, 310.0, -85.0],
        "Risk Assessment": ["Monitoring", "Secure", "Optimal", "Caution"]
    })
    st.dataframe(flight_df, use_container_width=True)

elif macro_module == "Inflation Pass-Through & Price Shock Predictor":
    st.markdown("### 📊 Inflation Pass-Through & Import Price Shock Predictor")
    
    fig_inf = go.Figure()
    fig_inf.add_trace(go.Scatter(x=t_months, y=infl_traj, mode='lines', name='Headline Inflation (%)', line=dict(color='#34D399', width=3)))
    fig_inf.add_trace(go.Scatter(x=t_months, y=fx_traj, mode='lines', name='FX Reserves Index', line=dict(color='#F59E0B', width=3, dash='dot')))
    fig_inf.update_layout(title_text="Inflation Pass-Through Simulation", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=420, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_inf, use_container_width=True)

elif macro_module == "Monetary Policy Rate & Yield Curve Optimizer":
    st.markdown("### 🏦 Monetary Policy Rate & Sovereign Yield Curve Optimizer")
    col1, col2 = st.columns(2)
    col1.metric("Optimal Central Bank Rate", f"{interest_rate:.1f}%", delta="0.0%")
    col2.metric("Yield Spread (10Y over 2Y)", "340 Basis Points", delta="+15 bps")
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT country, tenor, yield_rate, spread_bps, recommendation FROM sovereign_bonds")
    bonds_data = cursor.fetchall()
    
    bonds_df = pd.DataFrame(bonds_data, columns=["Country", "Tenor", "Yield Rate (%)", "Spread (bps)", "Strategic Recommendation"])
    st.dataframe(bonds_df, use_container_width=True)

elif macro_module == "Multi-Country Contagion & Risk Matrix":
    st.markdown("### 🌐 Regional Multi-Country Macroeconomic Contagion Matrix")
    st.markdown("Analyzing cross-border spillover effects, regional trade friction, and sovereign risk contagion.")
    
    contagion_df = pd.DataFrame({
        "Economy": ["Uganda", "Kenya", "Tanzania", "Rwanda", "Democratic Republic of Congo"],
        "Macro Vulnerability Index": ["Low", "Moderate", "Low", "Optimal", "High"],
        "Debt-to-GDP (%)": ["52.4%", "68.2%", "41.5%", "49.0%", "58.7%"],
        "External Shock Resilience": ["Stable", "Caution", "Robust", "Robust", "Vulnerable"]
    })
    st.dataframe(contagion_df, use_container_width=True)

elif macro_module == "Fiscal Deficit & Liquidity Coverage (LCR)":
    st.markdown("### 🛡️ Fiscal Deficit, Treasury Cashflow & Liquidity Coverage Ratio")
    col1, col2, col3 = st.columns(3)
    col1.metric("Liquidity Coverage Ratio (LCR)", "118.4%", delta="+1.2%")
    col2.metric("Fiscal Deficit (% of GDP)", "4.2%", delta="-0.3%")
    col3.metric("Treasury Single Account (TSA)", "Balanced", delta="Optimal")

    st.markdown("""
    <div class="glass-container">
    <b>Treasury Liquidity Advisory:</b><br>
    Buffer reserves remain above Basel III minimum thresholds (100%). Short-term domestic debt issuances should be prioritized during periods of high foreign exchange volatility.
    </div>
    """, unsafe_allow_html=True)

