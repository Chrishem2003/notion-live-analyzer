import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import pandas as pd
import json
import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Global Sovereign Interactive Command & Intelligence Core",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Professional Enterprise Styling ---
st.markdown("""
    <style>
    .main-header { font-size: 2.3rem; font-weight: 800; color: #0F172A; margin-bottom: 0rem; letter-spacing: -0.5px; }
    .sub-header { font-size: 1.1rem; color: #475569; margin-bottom: 1.5rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] { background-color: #F1F5F9; border-radius: 6px; padding: 8px 14px; font-weight: 600; color: #334155; }
    .stTabs [aria-selected="true"] { background-color: #1E3A8A !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- Session State Management for Interactive Chat ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Sovereign Intelligence Core online. Type commands or query data parameters below."}
    ]

# --- Sidebar: Full Interactive Control ---
st.sidebar.markdown("## 👑 Interactive Control Hub")

target_country = st.sidebar.text_input("Active Jurisdiction / Country", "🇺🇬 Uganda (National Focus)")
sector = st.sidebar.text_input("Active Sector / Problem Domain", "Higher Education & Public Infrastructure")

user_role = st.sidebar.selectbox(
    "Select Interface View Mode",
    [
        "💬 Interactive Conversational Command Core", 
        "📈 Advanced Graphical Trend Suite",
        "⚖️ Multi-Scenario Policy Battleground",
        "📄 Export & Ministerial Briefing Center"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Simulation Variables")
a = st.sidebar.slider("System Influx / Growth Rate ($a$)", 0.1, 5.0, 2.1, 0.1)
b = st.sidebar.slider("Operational Friction / Overhead ($b$)", 0.0, 3.0, 0.9, 0.1)
c = st.sidebar.slider("Buffer Decay ($c$)", 0.0, 3.0, 1.0, 0.1)
policy_shock = st.sidebar.slider("Crisis Shock Magnitude", -3.0, 3.0, 0.0, 0.1)
t_max = st.sidebar.slider("Forecast Time Horizon", 50, 500, 200, 10)

# --- Mathematical Engine Core ---
def system_ode(state, t, a, b, c, shock_val):
    x, y, z = state
    shock = shock_val if (45 <= t <= 55) else 0.0
    dxdt = x - z - (y - a) * x + shock
    dydt = 1 - b * y - x**2
    dzdt = x - c * z
    return [dxdt, dydt, dzdt]

t = np.linspace(0, t_max, t_max * 10)
initial_state = [0.1, 0.1, 0.1]
solution = odeint(system_ode, initial_state, t, args=(a, b, c, policy_shock))
x_traj, y_traj, z_traj = solution[:, 0], solution[:, 1], solution[:, 2]

perturbation_growth = np.abs(np.gradient(x_traj)) + 0.05
mlce_value = np.mean(np.log(perturbation_growth + 1e-5)) / (t[1] - t[0])

# --- Main Interface Modes ---

# 1. Interactive Conversational Command Core
if "Conversational Command" in user_role:
    st.markdown('<p class="main-header">💬 Sovereign Conversational Intelligence Hub</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-header">Direct text-based telemetry interaction for <b>{target_country}</b> across sector: <b>{sector}</b></p>', unsafe_allow_html=True)

    # Render chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User chat text input box
    user_prompt = st.chat_input("Enter command, query metrics, or request policy advice...")
    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Dynamic Response Generation based on User Text
        prompt_lower = user_prompt.lower()
        if "status" in prompt_lower or "health" in prompt_lower:
            reply = f"Current stability index (mLCE) for {target_country} is **{mlce_value:.4f}**. System status is officially classified as **{'CRITICAL RISK' if mlce_value > 0 else 'SECURE'}**."
        elif "shock" in prompt_lower:
            reply = f"Active crisis shock magnitude is set to **{policy_shock}x**. Window occurs between t=45 and t=55."
        elif "help" in prompt_lower:
            reply = "You can ask for 'status', request 'metrics', query 'shock analysis', or type custom sector configurations into the sidebar."
        else:
            reply = f"Command received and logged for **{target_country}** [{sector}]. Current mathematical convergence index reads {mlce_value:.4f} under friction parameter b={b}."

        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

# 2. Advanced Graphical Trend Suite
elif "Graphical Trend Suite" in user_role:
    st.markdown('<p class="main-header">📈 Advanced Graphical Trend Suite</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-header">Deep visual inspection of trajectory flows, variance spikes, and phase space attractors.</p>', unsafe_allow_html=True)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Primary Performance & Shock Window")
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(t, x_traj, color='#1E3A8A', lw=2, label='Primary Trajectory ($X$)')
        ax.plot(t, y_traj, color='#10B981', lw=1.5, linestyle='--', label='Resource Flow ($Y$)')
        ax.axvspan(45, 55, color='#DC2626', alpha=0.2, label='Shock Window')
        ax.set_xlabel("Time Steps")
        ax.set_ylabel("Normalized Index")
        ax.legend(loc='upper right')
        ax.grid(True, linestyle="--", alpha=0.5)
        st.pyplot(fig)

    with col_g2:
        st.subheader("Critical Slowing Down (Variance Spikes)")
        window = 20
        rolling_var = [np.var(x_traj[max(0, i-window):i]) for i in range(1, len(x_traj)+1)]
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        ax2.plot(t, rolling_var, color='#DC2626', lw=2, label='Rolling Variance')
        ax2.set_xlabel("Time Steps")
        ax2.set_ylabel("Variance Magnitude")
        ax2.grid(True, linestyle="--", alpha=0.5)
        st.pyplot(fig2)

# 3. Multi-Scenario Policy Battleground
elif "Policy Battleground" in user_role:
    st.markdown('<p class="main-header">⚖️ Multi-Scenario Policy Comparison Matrix</p>', unsafe_allow_html=True)
    
    sol_base = solution[:, 0]
    sol_sub = odeint(system_ode, initial_state, t, args=(a, b - 0.3, c, policy_shock * 0.5))[:, 0]
    sol_ref = odeint(system_ode, initial_state, t, args=(a * 0.8, b, c, 0.0))[:, 0]

    fig_m, ax_m = plt.subplots(figsize=(10, 4.5))
    ax_m.plot(t, sol_base, color='#DC2626', lw=2, label='Option 1: Do Nothing (Baseline)')
    ax_m.plot(t, sol_sub, color='#3B82F6', lw=2, linestyle='--', label='Option 2: Emergency Subsidization')
    ax_m.plot(t, sol_ref, color='#10B981', lw=2, linestyle='-.', label='Option 3: Structural Damping')
    ax_m.set_title(f"Strategic Comparison for {target_country} — {sector}")
    ax_m.set_xlabel("Time Horizon")
    ax_m.set_ylabel("System Health Score")
    ax_m.legend()
    ax_m.grid(True, linestyle="--", alpha=0.5)
    st.pyplot(fig_m)

# 4. Export & Ministerial Briefing Center
else:
    st.markdown('<p class="main-header">📄 Export & Ministerial Briefing Center</p>', unsafe_allow_html=True)
    st.markdown("Download full structured datasets, telemetry logs, or official executive briefing texts.")

    report_content = f"""SOVEREIGN MINISTERIAL BRIEFING REPORT
Jurisdiction: {target_country}
Sector: {sector}
Timestamp: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
--------------------------------------------------
Instability Index (mLCE): {mlce_value:.4f}
System Regime Status: {'CRITICAL RISK' if mlce_value > 0 else 'SECURE'}
Active Policy Shock: {policy_shock}x
"""

    st.text_area("Generated Executive Text Briefing", report_content, height=150)
    
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            label="📥 Download Ministerial Briefing (.txt)",
            data=report_content,
            file_name="ministerial_briefing.txt",
            mime="text/plain"
        )
    with col_dl2:
        df_export = pd.DataFrame({"Time": t, "Metric_X": x_traj, "Metric_Y": y_traj, "Metric_Z": z_traj})
        st.download_button(
            label="📥 Download Full Telemetry Logs (.csv)",
            data=df_export.to_csv(index=False).encode('utf-8'),
            file_name="sovereign_telemetry_logs.csv",
            mime="text/csv"
        )
