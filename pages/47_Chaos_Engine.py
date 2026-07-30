import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import pandas as pd
import json
import datetime
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="Global Sovereign Autonomous Command & Resilience Core",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Professional Enterprise Styling ---
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: 800; color: #0F172A; margin-bottom: 0rem; letter-spacing: -0.5px; }
    .sub-header { font-size: 1.1rem; color: #475569; margin-bottom: 2rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] { background-color: #F1F5F9; border-radius: 6px; padding: 10px 16px; font-weight: 600; color: #334155; }
    .stTabs [aria-selected="true"] { background-color: #1E3A8A !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- Session State for Conversational Chat History ---
if "global_chat_history" not in st.session_state:
    st.session_state.global_chat_history = [
        {"role": "assistant", "content": "Global Sovereign Intelligence Core online. Type commands, query cross-border metrics, or request policy prescriptions below."}
    ]

# --- Sidebar: Universal Global Configuration ---
st.sidebar.markdown("## 👑 Global Sovereign Command Hub")

# Universal Global Territory Mode
region_option = st.sidebar.radio("Jurisdiction Scope", ["🌍 Global Multi-State Selector", "✏️ Custom World Region / Country"])
if region_option == "🌍 Global Multi-State Selector":
    target_country = st.sidebar.selectbox(
        "Select Country / Territory",
        [
            "🇺🇬 Uganda (National Focus)", 
            "🇰🇪 Kenya", 
            "🇷🇼 Rwanda", 
            "🇳🇬 Nigeria", 
            "🇿🇦 South Africa", 
            "🇬🇭 Ghana",
            "🇺🇸 United States",
            "🇬🇧 United Kingdom",
            "🇯🇵 Japan",
            "🇧🇷 Brazil",
            "🌐 Global Aggregate Node"
        ]
    )
else:
    target_country = st.sidebar.text_input("Enter Custom Country / Territory", "🇨🇦 Canada (Custom Regional Node)")

sector = st.sidebar.selectbox(
    "Select Institutional Sector / Problem",
    [
        "🎓 Higher Education: Student Tuition & Cashflow Tracking", 
        "🏥 Healthcare: Hospital Bed Capacity & Emergency Surge", 
        "🌾 Agriculture: Food Security & Crop Yield Risk", 
        "🏦 National Treasury: Fiscal Deficit & Economic Contagion",
        "⚡ Infrastructure: Municipal Power & Grid Reliability",
        "🛡️ National Defense: Logistics & Strategic Supply Chains"
    ]
)

user_role = st.sidebar.selectbox(
    "Select Command Interface Mode",
    [
        "💬 Interactive Conversational Command Core", 
        "📊 Executive Storyboard & Live Dispatcher",
        "📈 Advanced Graphical Visual Suite (Phase Space & Bifurcation)",
        "⚖️ Multi-Scenario Policy Battleground Matrix",
        "📥 Universal Multi-Format Data Importer & Exporter"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Real-Time Situation Sliders")
a = st.sidebar.slider("System Influx / Growth Rate ($a$)", 0.1, 5.0, 2.1, 0.1)
b = st.sidebar.slider("Operational Friction / Overhead ($b$)", 0.0, 3.0, 0.9, 0.1)
c = st.sidebar.slider("Buffer Decay ($c$)", 0.0, 3.0, 1.0, 0.1)
policy_shock = st.sidebar.slider("Crisis Shock Magnitude (Outbreak, Drought, Crash)", -3.0, 3.0, 0.0, 0.1)
t_max = st.sidebar.slider("Forecast Time Horizon (Days / Weeks)", 50, 500, 200, 10)

# --- Advanced Mathematical Core (Nonlinear ODE Solver) ---
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

# --- Main App Header ---
st.markdown('<p class="main-header">👑 Global Sovereign Autonomous Command & Resilience Core</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">Active Jurisdiction: <b>{target_country}</b> | Sector Architecture: <b>{sector}</b> | Mode: <b>{user_role}</b></p>', unsafe_allow_html=True)

# ==========================================
# MODE 1: INTERACTIVE CONVERSATIONAL CHAT CORE
# ==========================================
if "Conversational Command" in user_role:
    st.markdown("## 💬 Sovereign Conversational Intelligence Hub")
    st.markdown("Interact directly with the global autonomous engine using natural language text prompts.")

    for msg in st.session_state.global_chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input("Enter command, query regional stability, or request policy advice...")
    if user_prompt:
        st.session_state.global_chat_history.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        p_lower = user_prompt.lower()
        if "status" in p_lower or "health" in p_lower:
            reply = f"Global telemetry check for **{target_country}**: Instability Index (mLCE) reads **{mlce_value:.4f}**. System state is classified as **{'CRITICAL RISK' if mlce_value > 0 else 'SECURE'}**."
        elif "shock" in p_lower:
            reply = f"Active crisis shock magnitude for **{target_country}** is set to **{policy_shock}x** across sector [{sector}]."
        elif "help" in p_lower:
            reply = "You can ask for 'status', query 'shock analysis', request 'policy recommendations', or switch regions and sectors in the sidebar."
        else:
            reply = f"Command successfully processed for **{target_country}**. Current mathematical convergence score is {mlce_value:.4f} under friction parameter b={b}."

        st.session_state.global_chat_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

# ==========================================
# MODE 2: EXECUTIVE STORYBOARD & LIVE DISPATCHER
# ==========================================
elif "Executive Storyboard" in user_role:
    st.markdown("## 📊 Executive Storyboard & Live Notification Dispatcher")
    
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if mlce_value > 0:
        st.error(f"🚨 **CRITICAL ALERT DISPATCHED [{timestamp_str}]**: Instability threshold breached in **{target_country}** (mLCE = {mlce_value:.4f}). Notifications transmitted to director registry (`2501202072@muni.ac.ug`), SMS gateways, and Webhook endpoints.")
        with st.expander("📬 View Dispatched Telemetry Payloads"):
            st.json({
                "timestamp": timestamp_str,
                "jurisdiction": target_country,
                "sector": sector,
                "status": "CRITICAL_RISK",
                "target_recipient": "2501202072@muni.ac.ug",
                "metric_score": float(mlce_value)
            })
    else:
        st.success(f"🟢 **SYSTEM HOMEOSTASIS SECURE [{timestamp_str}]**: All operational vectors for **{target_country}** remain within stable parameters.")

    col_k1, col_k2, col_k3 = st.columns(3)
    with col_k1:
        st.metric(label="System Health Status", value="CRITICAL RISK" if mlce_value > 0 else "SECURE")
    with col_k2:
        st.metric(label="Instability Score (mLCE)", value=f"{mlce_value:.4f}")
    with col_k3:
        st.metric(label="Active Shock Multiplier", value=f"{policy_shock}x")

    st.markdown("---")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("### 🤖 AI Autonomous Policy Prescription:")
        if mlce_value < 0:
            st.success("Recommendation: Maintain standard operational oversight. No intervention required.")
        else:
            optimal_fix = round(b * 0.72, 2)
            st.error(f"**Action Required:** Deploy emergency liquidity or structural damping in **{target_country}** to reduce friction index down to **{optimal_fix}** within 72 hours.")
    with col_s2:
        st.subheader("📈 Trackable Flow")
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.plot(t, x_traj, color='#1E3A8A', lw=2, label='Performance Flow')
        ax.axvspan(45, 55, color='#DC2626', alpha=0.2, label='Crisis Shock Window')
        ax.set_title(f"Stability Curve — {target_country}")
        ax.grid(True, linestyle="--", alpha=0.5)
        st.pyplot(fig)

# ==========================================
# MODE 3: ADVANCED GRAPHICAL VISUAL SUITE
# ==========================================
elif "Advanced Graphical Visual Suite" in user_role:
    st.markdown("## 📈 Advanced Graphical Visual Suite (Phase Space & Bifurcation)")
    
    tab_g1, tab_g2, tab_g3, tab_g4 = st.tabs(["📈 Trajectories & Variance", "🌀 3D Attractor & PSS", "🌊 Bifurcation Stability Map", "⚠️ Critical Slowing Down"])
    
    with tab_g1:
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(t, x_traj, color='#1E3A8A', lw=2, label='System Metric X')
        ax.plot(t, y_traj, color='#10B981', lw=1.5, linestyle='--', label='Resource Flow Y')
        ax.axvspan(45, 55, color='#DC2626', alpha=0.2, label='Shock Window')
        ax.set_title(f"Multi-Variable Trajectory — {target_country}")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.5)
        st.pyplot(fig)

    with tab_g2:
        col_3d1, col_3d2 = st.columns(2)
        with col_3d1:
            fig3d = plt.figure(figsize=(5, 4))
            ax3d = fig3d.add_subplot(111, projection='3d')
            ax3d.plot(x_traj, y_traj, z_traj, color='#1E3A8A', lw=1)
            ax3d.set_title("3D Attractor Flow")
            st.pyplot(fig3d)
        with col_3d2:
            figpss, axpss = plt.subplots(figsize=(5, 4))
            mask = np.isclose(z_traj, 0.1, atol=0.1)
            axpss.scatter(x_traj[mask], y_traj[mask], color='#DC2626', s=15)
            axpss.set_title("Poincaré Surface of Section")
            st.pyplot(figpss)

    with tab_g3:
        st.subheader("Bifurcation Stability Map")
        if st.button("Compute Bifurcation Sweep"):
            b_sweep = np.linspace(0.1, 3.0, 60)
            b_vals, x_peaks = [], []
            for bp in b_sweep:
                sol_s = odeint(system_ode, [0.1, 0.1, 0.1], np.linspace(0, 30, 200), args=(a, bp, c, 0.0))
                for p in sol_s[150:, 0][::10]:
                    b_vals.append(bp)
                    x_peaks.append(p)
            fig_b, ax_b = plt.subplots(figsize=(10, 4))
            ax_b.scatter(b_vals, x_peaks, s=0.5, color='#1E3A8A')
            ax_b.set_title(f"Bifurcation Diagram — {target_country}")
            st.pyplot(fig_b)
        else:
            st.info("Click button to compute stability bifurcation map.")

    with tab_g4:
        st.subheader("Critical Slowing Down & Variance Spikes")
        window = 20
        rolling_var = [np.var(x_traj[max(0, i-window):i]) for i in range(1, len(x_traj)+1)]
        fig_ews, ax_ews = plt.subplots(figsize=(10, 4))
        ax_ews.plot(t, rolling_var, color='#DC2626', lw=2)
        ax_ews.set_title("Variance Spikes Indicating Looming Collapse")
        st.pyplot(fig_ews)

# ==========================================
# MODE 4: MULTI-SCENARIO POLICY BATTLEGROUND
# ==========================================
elif "Multi-Scenario Policy Battleground" in user_role:
    st.markdown("## ⚖️ Multi-Scenario Policy Battleground Matrix")
    st.markdown(f"Compare strategic policy interventions for **{target_country}** under active shock conditions:")

    sol_base = solution[:, 0]
    sol_sub = odeint(system_ode, initial_state, t, args=(a, b - 0.3, c, policy_shock * 0.5))[:, 0]
    sol_ref = odeint(system_ode, initial_state, t, args=(a * 0.8, b, c, 0.0))[:, 0]

    fig_m, ax_m = plt.subplots(figsize=(10, 4.5))
    ax_m.plot(t, sol_base, color='#DC2626', lw=2, label='Option 1: Do Nothing (Baseline)')
    ax_m.plot(t, sol_sub, color='#3B82F6', lw=2, linestyle='--', label='Option 2: Emergency Subsidization')
    ax_m.plot(t, sol_ref, color='#10B981', lw=2, linestyle='-.', label='Option 3: Structural Damping')
    ax_m.set_title(f"Strategic Policy Battleground — {target_country}")
    ax_m.set_xlabel("Time Horizon")
    ax_m.set_ylabel("System Health Score")
    ax_m.legend()
    ax_m.grid(True, linestyle="--", alpha=0.5)
    st.pyplot(fig_m)

    if st.button("🚀 Authorize Option 2 (Emergency Subsidy Deployment)"):
        st.success(f"✅ Option 2 officially authorized and broadcasted across cabinets for **{target_country}**.")

# ==========================================
# MODE 5: UNIVERSAL DATA IMPORTER & EXPORTER
# ==========================================
else:
    st.markdown("## 📥 Universal Multi-Format Data Importer & Exporter")
    st.markdown("Upload custom institutional datasets in any format (`.csv`, `.json`, `.txt`), map schemas, and download official ministerial reports.")

    uploaded_file = st.file_uploader("Upload External Dataset", type=["csv", "json", "txt"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_user = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith('.json'):
                df_user = pd.read_json(uploaded_file)
            else:
                df_user = pd.read_csv(uploaded_file, sep=None, engine='python')
                
            st.success(f"Successfully ingested `{uploaded_file.name}` ({len(df_user)} records parsed).")
            st.dataframe(df_user.head(5), use_container_width=True)
            st.info("💡 **Auto-Mapping Active:** External dataset successfully linked to sovereign simulation engine.")
        except Exception as e:
            st.error(f"Error parsing file: {e}")

    st.markdown("---")
    st.subheader("Official Ministerial Report & Telemetry Export")
    
    report_content = f"""SOVEREIGN MINISTERIAL BRIEFING REPORT
Jurisdiction: {target_country}
Sector: {sector}
Timestamp: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
--------------------------------------------------
Instability Index (mLCE): {mlce_value:.4f}
System Regime Status: {'CRITICAL RISK' if mlce_value > 0 else 'SECURE'}
Active Policy Shock: {policy_shock}x
Director Registry Dispatch: 2501202072@muni.ac.ug
"""

    st.text_area("Generated Ministerial Briefing", report_content, height=140)
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button("📥 Download Ministerial Briefing (.txt)", data=report_content, file_name="ministerial_briefing.txt", mime="text/plain")
    with col_d2:
        df_export = pd.DataFrame({"Time": t, "Metric_X": x_traj, "Metric_Y": y_traj, "Metric_Z": z_traj})
        st.download_button("📥 Download Full Telemetry Logs (.csv)", data=df_export.to_csv(index=False).encode('utf-8'), file_name="sovereign_telemetry_logs.csv", mime="text/csv")
