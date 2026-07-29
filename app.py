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

# Initialize Database Backend
init_db()

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

