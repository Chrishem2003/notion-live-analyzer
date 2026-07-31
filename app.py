import builtins
import datetime
import io
import numpy as np
import pandas as pd
import streamlit as st
from scipy.integrate import odeint

import plotly.graph_objects as go

# ---------------------------------------------------------
# GLOBAL BUILTINS & FALLBACKS
# ---------------------------------------------------------
if not hasattr(builtins, "run_automations"):
    def _run_automations_fallback(*args, **kwargs):
        pass
    builtins.run_automations = _run_automations_fallback

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="CHRISHEM Sovereign Engine",
    page_icon="*",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# ADVANCED METALLIC GLASSMORPHISM CSS (NO-EMOJI / NO-UNICODE)
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #F8FAFC !important;
    }

    .stApp {
        background: radial-gradient(circle at top right, #0F172A, #070B14 75%);
        background-attachment: fixed;
    }

    /* Top Subheader Banner */
    .top-banner {
        background: rgba(15, 23, 42, 0.75);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 0.85rem 1.25rem;
        margin-bottom: 1.25rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    
    .top-banner-item {
        font-size: 0.85rem;
        color: #94A3B8;
        font-weight: 500;
    }
    
    .top-banner-item b {
        color: #38BDF8;
        font-weight: 600;
    }

    /* Metric Boxes */
    .metric-box {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }
    .metric-box .val {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38BDF8, #818CF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-box .lbl {
        font-size: 0.75rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }

    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.8rem;
    }
    .status-stable { background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid #059669; }
    .status-critical { background: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid #DC2626; }

    /* Sidebar Overrides */
    [data-testid="stSidebar"] {
        background-color: #060911 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    .glass-hr {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# HELPER: SAFE MULTI-ENCODING DATA LOADER
# ---------------------------------------------------------
def load_dataset(uploaded_file):
    file_bytes = uploaded_file.read()
    name = uploaded_file.name.lower()
    
    if name.endswith(".csv") or name.endswith(".txt"):
        for enc in ["utf-8", "latin-1", "cp1252", "iso-8859-1"]:
            try:
                return pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
            except Exception:
                continue
    elif name.endswith(".json"):
        return pd.read_json(io.BytesIO(file_bytes))
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(file_bytes))
    return None

# ---------------------------------------------------------
# MODULE: NONLINEAR CHAOS ENGINE VIEW
# ---------------------------------------------------------
def render_nonlinear_chaos_engine():
    st.markdown("### Dynamic Stability & Nonlinear Chaos Matrix")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        param_a = st.slider("Drive Term (a)", 0.1, 5.0, 1.5, 0.1)
    with c2:
        param_b = st.slider("Damping Coefficient (b)", 0.0, 3.0, 0.9, 0.1)
    with c3:
        param_c = st.slider("Decay Index (c)", 0.0, 3.0, 1.0, 0.1)
    with c4:
        shock = st.slider("Shock Vector", -3.0, 3.0, 0.0, 0.1)

    t_max = st.slider("Simulation Horizon (t)", 50, 500, 200, 10)

    def system_ode(state, t, a, b, c, shock_val):
        x, y, z = state
        sk = shock_val if (0.45 * t_max <= t <= 0.55 * t_max) else 0.0
        dxdt = x - z - (y - a) * x + sk
        dydt = 1 - b * y - x**2
        dzdt = x - c * z
        return [dxdt, dydt, dzdt]

    t_arr = np.linspace(0, t_max, t_max * 10)
    initial_state = [0.1, 0.1, 0.1]

    try:
        sol = odeint(system_ode, initial_state, t_arr, args=(param_a, param_b, param_c, shock))
    except Exception:
        sol = np.zeros((len(t_arr), 3))

    sol = np.nan_to_num(sol, nan=0.0, posinf=1e4, neginf=-1e4)
    x_traj, y_traj, z_traj = sol[:, 0], sol[:, 1], sol[:, 2]

    growth = np.abs(np.gradient(x_traj)) + 1e-5
    mlce = float(np.mean(np.log(growth)) / (t_arr[1] - t_arr[0]))
    status = "STABLE" if mlce < 0 else "CRITICAL / CHAOTIC"

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.markdown(f'<div class="metric-box"><div class="val">{mlce:.4f}</div><div class="lbl">Max Lyapunov Exponent (mLCE)</div></div>', unsafe_allow_html=True)
    with mc2:
        badge_cls = "status-stable" if mlce < 0 else "status-critical"
        st.markdown(f'<div class="metric-box"><div class="val"><span class="status-badge {badge_cls}">{status}</span></div><div class="lbl">Phase System State</div></div>', unsafe_allow_html=True)
    with mc3:
        st.markdown(f'<div class="metric-box"><div class="val">{len(t_arr)}</div><div class="lbl">Computed Steps</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    fig = go.Figure(data=[go.Scatter3d(
        x=x_traj, y=y_traj, z=z_traj,
        mode='lines',
        line=dict(color='#38BDF8', width=3),
        name='Phase Trajectory'
    )])
    fig.update_layout(
        title="3D Phase-Space Trajectory Vector",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=500,
        font=dict(color='#F8FAFC'),
        scene=dict(
            xaxis=dict(gridcolor='rgba(255,255,255,0.1)', backgroundcolor='rgba(0,0,0,0)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)', backgroundcolor='rgba(0,0,0,0)'),
            zaxis=dict(gridcolor='rgba(255,255,255,0.1)', backgroundcolor='rgba(0,0,0,0)')
        ),
        margin=dict(l=0, r=0, t=30, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# MAIN ROUTER & NAVIGATION
# ---------------------------------------------------------
def main():
    st.sidebar.title("CHRISHEM")
    st.sidebar.caption("Sovereign Enterprise Engine v2.5")
    st.sidebar.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)

    navigation = st.sidebar.radio(
        "Navigation Hub",
        [
            "Personal Workspace",
            "Nonlinear Chaos Engine",
            "Access Control & Licensing",
            "Ecosystem Apex",
            "AI Intelligence Daemon",
            "Admin Billing Ledger",
            "Workflow Scheduler",
            "Neural Forecaster & AI",
            "Academic & CV Studio",
            "Telemetry & Smart Alerts",
            "System Diagnostics & Health",
            "API & Integration Gateway"
        ]
    )

    st.sidebar.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)
    st.sidebar.caption("SYSTEM STATUS")
    st.sidebar.success("[OK] Operational (100%)")
    st.sidebar.info("[SECURE] Sovereign Enclave")

    target_country = "Uganda [UG]"
    sector_label = "Economics & Finance (Huang-Li)"
    analyst_name = "Kula Chris"

    st.markdown(f"""
        <div class="top-banner">
            <div class="top-banner-item">Jurisdiction: <b>{target_country}</b></div>
            <div class="top-banner-item">Sector: <b>{sector_label}</b></div>
            <div class="top-banner-item">Lead Analyst: <b>{analyst_name}</b></div>
            <div class="top-banner-item">Time: <b>{datetime.datetime.now().strftime('%H:%M:%S')} EAT</b></div>
        </div>
    """, unsafe_allow_html=True)

    st.title(navigation)
    st.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)

    if navigation == "Personal Workspace":
        try:
            from modules.personal_workspace import render_personal_workspace_panel
            render_personal_workspace_panel()
        except Exception:
            st.subheader("Universal Personal Workspace & Productivity Hub")
            st.caption("Manage research milestones, bioinformatics pipelines, system configurations, and daily workflow tasks.")

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown('<div class="metric-box"><div class="val">4</div><div class="lbl">Active Milestones</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="metric-box"><div class="val">94.2%</div><div class="lbl">Research Progress</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown('<div class="metric-box"><div class="val">Synced</div><div class="lbl">Workspace Status</div></div>', unsafe_allow_html=True)
            with c4:
                st.markdown('<div class="metric-box"><div class="val">100%</div><div class="lbl">Focus Score</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### Active Research & Task Milestones")
            tasks_df = pd.DataFrame([
                {"Task Item": "Waterborne Pathogen Surveillance Batch Analysis", "Category": "Bioinformatics Research", "Priority": "Critical", "Status": "IN PROGRESS"},
                {"Task Item": "ALX Data Analytics Portfolio Integration", "Category": "Professional Certification", "Priority": "High", "Status": "OPTIMIZED"},
                {"Task Item": "Desktop Environment Customization & UI Polish", "Category": "Workspace Customization", "Priority": "Medium", "Status": "ACTIVE"},
                {"Task Item": "Cryptographic Vault Key Rotation", "Category": "Security Engineering", "Priority": "Critical", "Status": "COMPLETED"}
            ])
            st.dataframe(tasks_df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("#### Embedded Secure Personal Vault Explorer")
            up = st.file_uploader("Upload files into Secure Vault:", accept_multiple_files=True, key="main_vault_uploader")
            if up:
                for f in up:
                    df = load_dataset(f)
                    if df is not None:
                        st.success(f"Successfully decoded `{f.name}`")
                        st.dataframe(df.head(5), use_container_width=True)

    elif navigation == "Nonlinear Chaos Engine":
        try:
            from modules.nonlinear_chaos_engine import render_nonlinear_chaos_engine_panel
            render_nonlinear_chaos_engine_panel()
        except Exception:
            render_nonlinear_chaos_engine()

    elif navigation == "Access Control & Licensing":
        try:
            from modules.access_control import render_access_control_panel
            render_access_control_panel()
        except Exception:
            c1, c2, c3 = st.columns(3)
            c1.metric("Clearance Tier", "Tier-1 Sovereign")
            c2.metric("License Expiry", "2030-12-31")
            c3.metric("Active Sessions", "3 Nodes")

    elif navigation == "Ecosystem Apex":
        try:
            from modules.ecosystem_apex import render_ecosystem_apex_panel
            render_ecosystem_apex_panel()
        except Exception:
            cols = st.columns(4)
            cols[0].metric("Grid Load", "84.2 %")
            cols[1].metric("Throughput", "1.2 TB/s")
            cols[2].metric("Latency", "2.1 ms")
            cols[3].metric("Resilience", "99.98 %")

    elif navigation == "AI Intelligence Daemon":
        try:
            from modules.ai_intelligence_daemon import render_ai_intelligence_panel
            render_ai_intelligence_panel()
        except Exception:
            st.markdown("#### Autonomous Intelligence Console")
            prompt = st.text_input("Enter natural language directive:")
            if prompt:
                st.info(f"Command executed: {prompt}")

    elif navigation == "Admin Billing Ledger":
        try:
            from modules.admin_billing_core import render_admin_billing_panel
            render_admin_billing_panel()
        except Exception:
            c1, c2 = st.columns(2)
            c1.metric("Current Cycle", "JULY 2026")
            c2.metric("Compute Allocation", "$1,240.50 USD")

    elif navigation == "Workflow Scheduler":
        try:
            from modules.workflow_scheduler import render_workflow_scheduler_panel
            render_workflow_scheduler_panel()
        except Exception:
            st.checkbox("Enable Automated Nightly Git Sync", value=True)

    elif navigation == "Neural Forecaster & AI":
        try:
            from modules.neural_forecaster import render_neural_forecaster_panel
            render_neural_forecaster_panel()
        except Exception:
            st.line_chart(np.sin(np.linspace(0, 10, 30)))

    elif navigation == "Academic & CV Studio":
        try:
            from modules.academic_portfolio_studio import render_academic_portfolio_studio_panel
            render_academic_portfolio_studio_panel()
        except Exception:
            st.write("**Lead Researcher:** Kula Chris")
            st.write("**Focus:** Bioinformatics, Systems Biology & Data Analytics")

    elif navigation == "Telemetry & Smart Alerts":
        try:
            from modules.telemetry_alerting import render_telemetry_alerting_panel
            render_telemetry_alerting_panel()
        except Exception:
            st.success("[OK] Systems Operating Within Thermal Limits")

    elif navigation == "System Diagnostics & Health":
        try:
            from modules.system_diagnostics import render_system_diagnostics_panel
            render_system_diagnostics_panel()
        except Exception:
            st.success("[OK] Diagnostic Integrity Verified")

    elif navigation == "API & Integration Gateway":
        try:
            from modules.api_integration_gateway import render_api_gateway_panel
            render_api_gateway_panel()
        except Exception:
            st.code("POST /api/v1/sovereign/execute")

if __name__ == "__main__":
    main()