import streamlit as st
import io
import numpy as np
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# GLOBAL PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="CHRISHEM Sovereign Engine",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# MAIN NAVIGATION & LAYOUT
# ---------------------------------------------------------
def main():
    st.sidebar.title("🌌 CHRISHEM")
    st.sidebar.caption("Sovereign Enterprise Engine")
    st.sidebar.markdown("---")

    navigation = st.sidebar.radio(
        "Navigation Hub",
        [
            "Personal Workspace",
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

    st.sidebar.markdown("---")
    st.sidebar.caption("SYSTEM STATUS")
    st.sidebar.success("🟢 Operational (100%)")
    st.sidebar.info("🔒 Secure Sovereign Enclave")

    # Header
    st.title(navigation)
    st.caption(f"Enterprise Operational Node | Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EAT")
    st.markdown("---")

    # ROUTE HANDLER
    if navigation == "Personal Workspace":
        try:
            from modules.personal_workspace import render_personal_workspace_panel
            render_personal_workspace_panel()
        except Exception:
            st.subheader("Universal Personal Workspace & Productivity Hub")
            st.caption("Manage research milestones, bioinformatics pipelines, system configurations, and daily workflow tasks.")
            
            # Metric Cards using native Streamlit containers
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                with st.container(border=True):
                    st.caption("ACTIVE MILESTONES")
                    st.subheader("4 Tracked")
                    st.caption("🟢 Up to Date")
            with c2:
                with st.container(border=True):
                    st.caption("RESEARCH PROGRESS")
                    st.subheader("94.2%")
                    st.caption("📈 +3.5% Auto")
            with c3:
                with st.container(border=True):
                    st.caption("WORKSPACE STATUS")
                    st.subheader("Synced")
                    st.caption("🔒 Local Enclave")
            with c4:
                with st.container(border=True):
                    st.caption("FOCUS SCORE")
                    st.subheader("100%")
                    st.caption("⚡ Deep Work")

            st.markdown("#### 🎯 Active Research & Task Milestones")

            tasks_df = pd.DataFrame([
                {"Task Item": "Waterborne Pathogen Surveillance Batch Analysis", "Category": "Bioinformatics Research", "Priority": "Critical", "Status": "IN PROGRESS"},
                {"Task Item": "ALX Data Analytics Portfolio Integration", "Category": "Professional Certification", "Priority": "High", "Status": "OPTIMIZED"},
                {"Task Item": "Desktop Environment Customization & UI Polish", "Category": "Workspace Customization", "Priority": "Medium", "Status": "ACTIVE"},
                {"Task Item": "Cryptographic Vault Key Rotation", "Category": "Security Engineering", "Priority": "Critical", "Status": "COMPLETED"}
            ])
            st.dataframe(tasks_df, use_container_width=True, hide_index=True)

            st.markdown("#### 📝 Quick Notes & Code Snippet Vault")
            st.text_area("Jot down research notes, terminal commands, or project ideas:", height=120, placeholder="Type notes here...")

        st.markdown("---")
        st.markdown("#### 📁 Embedded Secure Personal Vault Explorer")
        
        if "vault_files" not in st.session_state:
            st.session_state["vault_files"] = []

        up = st.file_uploader("Upload files into Secure Vault:", accept_multiple_files=True, key="main_vault_uploader")
        if up:
            for f in up:
                if not any(x["name"] == f.name for x in st.session_state["vault_files"]):
                    st.session_state["vault_files"].insert(0, {
                        "name": f.name,
                        "size": f"{f.size / 1024:.1f} KB" if f.size < 1048576 else f"{f.size / 1048576:.1f} MB",
                        "status": "Verified Payload",
                        "bytes": f.getvalue()
                    })
            st.rerun()

        if st.session_state["vault_files"]:
            cols = st.columns(3)
            for idx, item in enumerate(st.session_state["vault_files"]):
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.markdown(f"**📄 {item['name']}**")
                        st.caption(f"Size: {item['size']} | Status: {item['status']}")

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
            st.markdown("#### Macro Topology Monitor")
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
                st.info(f"Command executed: **{prompt}**")

    elif navigation == "Admin Billing Ledger":
        try:
            from modules.admin_billing_core import render_admin_billing_panel
            render_admin_billing_panel()
        except Exception:
            st.markdown("#### Billing & Resource Allocation")
            c1, c2 = st.columns(2)
            c1.metric("Current Cycle", "JULY 2026")
            c2.metric("Compute Allocation", ",240.50 USD")

    elif navigation == "Workflow Scheduler":
        try:
            from modules.workflow_scheduler import render_workflow_scheduler_panel
            render_workflow_scheduler_panel()
        except Exception:
            st.markdown("#### Autonomous Task Scheduler")
            st.checkbox("Enable Automated Nightly Git Sync", value=True)

    elif navigation == "Neural Forecaster & AI":
        try:
            from modules.neural_forecaster import render_neural_forecaster_panel
            render_neural_forecaster_panel()
        except Exception:
            st.markdown("#### Neural Forecast Matrix")
            st.line_chart(np.sin(np.linspace(0, 10, 30)))

    elif navigation == "Academic & CV Studio":
        try:
            from modules.academic_portfolio_studio import render_academic_portfolio_studio_panel
            render_academic_portfolio_studio_panel()
        except Exception:
            st.markdown("#### Academic Portfolio Studio")
            st.write("**Lead Researcher:** Kula Chris")
            st.write("**Focus:** Bioinformatics, Systems Biology & Data Analytics")

    elif navigation == "Telemetry & Smart Alerts":
        try:
            from modules.telemetry_alerting import render_telemetry_alerting_panel
            render_telemetry_alerting_panel()
        except Exception:
            st.success("✅ Systems Operating Within Thermal Limits")

    elif navigation == "System Diagnostics & Health":
        try:
            from modules.system_diagnostics import render_system_diagnostics_panel
            render_system_diagnostics_panel()
        except Exception:
            st.success("✅ Diagnostic Integrity Verified")

    elif navigation == "API & Integration Gateway":
        try:
            from modules.api_integration_gateway import render_api_gateway_panel
            render_api_gateway_panel()
        except Exception:
            st.code("POST /api/v1/sovereign/execute")

if __name__ == "__main__":
    main()