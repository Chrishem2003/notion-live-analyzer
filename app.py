import streamlit as st
from modules.database import init_db, log_backend_event
from modules.disk_monitor import render_disk_monitor_panel
from modules.env_auditor import render_env_auditor_panel
from modules.neural_sentinel import render_neural_sentinel_panel
from modules.quantum_vault import render_quantum_vault_panel
from modules.cluster_mesh import render_cluster_mesh_panel
from modules.threat_response import render_threat_response_panel
from modules.quantum_core import render_quantum_core_panel
from modules.award_command import render_award_command_panel
from modules.orbital_relay import render_orbital_relay_panel
from modules.biodefense_core import render_biodefense_panel
from modules.sovereign_singularity import render_sovereign_singularity_panel
from modules.ai_intelligence_daemon import render_ai_intelligence_panel
from modules.admin_billing_core import render_admin_billing_panel
from modules.personal_workspace import render_personal_workspace_panel
from modules.telemetry_alerting import render_telemetry_alerting_panel
from modules.system_diagnostics import render_system_diagnostics_panel
from modules.api_integration_gateway import render_api_gateway_panel
from modules.ecosystem_apex import render_ecosystem_apex_panel
from modules.workflow_scheduler import render_workflow_scheduler_panel
from modules.neural_forecaster import render_neural_forecaster_panel
from modules.academic_portfolio_studio import render_academic_portfolio_studio_panel
from modules.access_control import render_access_control_panel

# Initialize Database Backend
init_db()

# CHRISHEM Stunning UI Theme & Custom CSS Injection
st.markdown(
    \"\"\"
    <style>
        /* Global Dark Theme & Deep Space Aesthetic */
        .stApp {
            background-color: #090A0F;
            color: #E2E8F0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #0E1117;
            border-right: 1px solid #1E293B;
        }
        
        /* Metric Cards with Glassmorphism */
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
            border: 1px solid #334155;
            padding: 16px;
            border-radius: 12px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        [data-testid="stMetricLabel"] {
            color: #94A3B8 !important;
            font-weight: 600;
        }
        [data-testid="stMetricValue"] {
            color: #38BDF8 !important;
            font-weight: 700;
        }
        
        /* Buttons with Neon Glow */
        .stButton>button {
            background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%);
            color: white;
            border: 1px solid #38BDF8;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background: linear-gradient(135deg, #0369A1 0%, #075985 100%);
            border-color: #7DD3FC;
            box-shadow: 0 0 25px rgba(56, 189, 248, 0.6);
            transform: translateY(-2px);
        }
        
        /* Headers & Subheaders */
        h1, h2, h3 {
            color: #F8FAFC !important;
            letter-spacing: -0.025em;
        }
        
        /* Dataframes */
        [data-testid="stDataFrame"] {
            border: 1px solid #1E293B;
            border-radius: 10px;
            background-color: #0F172A;
        }
    </style>
    \"\"\",
    unsafe_allow_html=True
)

st.set_page_config(
    page_title="CHRISHEM Enterprise Intelligence Engine",
    page_icon="??",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("?? CHRISHEM Enterprise")
st.sidebar.caption("Sovereign Intelligence & Quantum Core")

navigation = st.sidebar.radio(
    "Navigation Command Center",
    [
        "Disk & Storage Monitor",
        "Environment & Secrets Auditor",
        "Neural Sentinel & Self-Healing",
        "Quantum Cryptographic Vault",
        "Global Cluster Mesh & Sync",
        "Incident Response & Containment",
        "Quantum Core & Neural Defense",
        "Award Command Center",
        "Orbital & Deep-Space Relay",
        "Biodefense & Pathogen Surveillance",
        "Sovereign Singularity Core"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("System Status: 100% Operational\nSecurity: Military-Grade Enclave")

if navigation == "Disk & Storage Monitor":
    render_disk_monitor_panel()
elif navigation == "Environment & Secrets Auditor":
    render_env_auditor_panel()
elif navigation == "Neural Sentinel & Self-Healing":
    render_neural_sentinel_panel()
elif navigation == "Quantum Cryptographic Vault":
    render_quantum_vault_panel()
elif navigation == "Global Cluster Mesh & Sync":
    render_cluster_mesh_panel()
elif navigation == "Incident Response & Containment":
    render_threat_response_panel()
elif navigation == "Quantum Core & Neural Defense":
    render_quantum_core_panel()
elif navigation == "Award Command Center":
    render_award_command_panel()
elif navigation == "Orbital & Deep-Space Relay":
    render_orbital_relay_panel()
elif navigation == "Biodefense & Pathogen Surveillance":
    render_biodefense_panel()
elif navigation == "Sovereign Singularity Core":
    render_sovereign_singularity_panel()












