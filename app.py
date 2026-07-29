
import streamlit as st
import os
from datetime import datetime
from modules.database import init_db, log_backend_event
from modules.theme_loader import apply_custom_theme
from modules.access_control import render_access_control_panel
from modules.ecosystem_apex import render_ecosystem_apex_panel
from modules.personal_workspace import render_personal_workspace_panel
from modules.ai_intelligence_daemon import render_ai_intelligence_panel
from modules.admin_billing_core import render_admin_billing_panel
from modules.workflow_scheduler import render_workflow_scheduler_panel
from modules.neural_forecaster import render_neural_forecaster_panel
from modules.academic_portfolio_studio import render_academic_portfolio_studio_panel
from modules.telemetry_alerting import render_telemetry_alerting_panel
from modules.system_diagnostics import render_system_diagnostics_panel
from modules.api_integration_gateway import render_api_gateway_panel

# Initialize Database & Page Config
init_db()

st.set_page_config(
    page_title="CHRISHEM Sovereign Enterprise Intelligence Engine",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply Neon Glassmorphism Theme
apply_custom_theme()

def main():
    st.sidebar.title("🌌 CHRISHEM Enterprise")
    st.sidebar.caption("Sovereign Intelligence & Autonomous Grid")
    
    navigation = st.sidebar.selectbox(
        "Navigation Hub",
        [
            "Access Control & Licensing",
            "Ecosystem Apex",
            "Personal Workspace",
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
    st.sidebar.info("System Status: 100% Operational\nEnclave: Secure Sovereign")

    if navigation == "Access Control & Licensing":
        render_access_control_panel()
    elif navigation == "Ecosystem Apex":
        render_ecosystem_apex_panel()
    elif navigation == "Personal Workspace":
        render_personal_workspace_panel()
    elif navigation == "AI Intelligence Daemon":
        render_ai_intelligence_panel()
    elif navigation == "Admin Billing Ledger":
        render_admin_billing_panel()
    elif navigation == "Workflow Scheduler":
        render_workflow_scheduler_panel()
    elif navigation == "Neural Forecaster & AI":
        render_neural_forecaster_panel()
    elif navigation == "Academic & CV Studio":
        render_academic_portfolio_studio_panel()
    elif navigation == "Telemetry & Smart Alerts":
        render_telemetry_alerting_panel()
    elif navigation == "System Diagnostics & Health":
        render_system_diagnostics_panel()
    elif navigation == "API & Integration Gateway":
        render_api_gateway_panel()

if __name__ == "__main__":
    main()

