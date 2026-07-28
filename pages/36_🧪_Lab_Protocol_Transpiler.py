"""
🧪 Advanced Theoretical-to-Practical Protocol Transpiler
High-performance computational laboratory workflow engine featuring automated stoichiometry mapping,
real-time biosafety compliance auditing, thermo-kinetic parameter optimization, and multi-format export pipelines.
"""
import streamlit as st

st.set_page_config(
    page_title="Theoretical-to-Practical Protocol Transpiler",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

from modules.lab_protocol_transpiler import (
    render_lab_protocol_transpiler_ui,
    init_transpiler_session_state,
    load_transpiler_stylesheet
)

# Initialize session state configuration and secure CSS injection pipelines
init_transpiler_session_state()
load_transpiler_stylesheet(is_dark=st.session_state.get("theme", "light") == "dark")

# ==========================================
# 1. ADVANCED TRANSPILER CONTROLS & HUD
# ==========================================

with st.sidebar:
    st.markdown("### ⚙️ Protocol Configuration")
    target_scale = st.selectbox(
        "Execution Scale Profile",
        ["Microfluidic High-Throughput (µL)", "Benchtop Standard (mL - L)", "Pilot Bioreactor (10L - 100L)", "Industrial Fermentation (kL+)"],
        key="transpiler_scale_profile"
    )
    
    st.markdown("---")
    st.markdown("### 🌡️ Kinetic & Environmental Parameters")
    temp_target = st.slider("Target Incubation Temperature (°C)", 4.0, 95.0, 37.0, 0.5, key="transpiler_temp")
    ph_buffer = st.slider("Buffer pH Tolerance Window", 2.0, 12.0, 7.4, 0.1, key="transpiler_ph")
    mixing_rpm = st.number_input("Agitation Speed (RPM)", min_value=0, max_value=3000, value=250, step=25, key="transpiler_rpm")
    
    st.markdown("---")
    st.markdown("### 🛡️ Compliance & Safety Flags")
    st.toggle("Biosafety Level (BSL) Automated Check", value=True, key="transpiler_bsl_toggle")
    st.toggle("Reagent Stoichiometry Auto-Correction", value=True, key="transpiler_stoich_toggle")
    st.toggle("Waste Neutralization Protocol Generation", value=True, key="transpiler_waste_toggle")

# ==========================================
# 2. MAIN TRANSPILER WORKSPACE
# ==========================================

# Render high-performance protocol transpiler UI with stateful parameter hooks
render_lab_protocol_transpiler_ui(
    scale_profile=target_scale,
    temperature=temp_target,
    target_ph=ph_buffer,
    agitation_rpm=mixing_rpm
)