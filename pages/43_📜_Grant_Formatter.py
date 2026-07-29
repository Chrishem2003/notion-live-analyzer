"""
📜 World-Class One-Click Grant & Journal Transpiler
Enterprise-grade academic publishing and funding proposal transformation engine featuring automated
guideline compliance parsing, multi-journal style mapping, tone adaptation, and structural gap analysis pipelines.
"""
import streamlit as st

st.set_page_config(
    page_title="One-Click Grant & Journal Transpiler",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. TRANSPILER SESSION STATE & CONFIGURATION
# ==========================================
if "grant_transpiler_active" not in st.session_state:
    st.session_state["grant_transpiler_active"] = False
if "target_output_profile" not in st.session_state:
    st.session_state["target_output_profile"] = "NIH / NSF Grant Proposal Standard"

from modules.grant_formatter import (
    render_grant_formatter_ui,
    init_grant_formatter_state,
    load_grant_formatter_stylesheet
)

# Initialize secure application state and responsive styling pipelines
init_grant_formatter_state()
load_grant_formatter_stylesheet(is_dark=st.session_state.get("theme", "light") == "dark")

# ==========================================
# 2. TRANSPILER CONTROL HUD & PARAMETERS
# ==========================================

with st.sidebar:
    st.markdown("### ⚙️ Target Destination Profile")
    output_profile = st.selectbox(
        "Formatting & Style Standard",
        [
            "NIH / NSF Grant Proposal Standard",
            "Nature / Science Research Article",
            "IEEE / ACM Conference Proceeding",
            "Elsevier / Springer Journal Track",
            "WHO / Gates Foundation Global Health Grant"
        ],
        key="grant_target_profile_select"
    )
    st.session_state["target_output_profile"] = output_profile

    st.markdown("---")
    st.markdown("### 🎛️ Optimization & Constraint Controls")
    word_limit = st.selectbox(
        "Strict Word Count Constraint",
        ["Unbounded (Full Draft)", "Strict 3,000 Words", "Strict 5,000 Words", "Strict 10,000 Words", "Custom Abstract Limit (250 Words)"],
        key="grant_word_limit_select"
    )
    tone_adaptation = st.selectbox(
        "Rhetorical Tone Adjustment",
        ["Academic Rigorous & Objective", "Persuasive & Impact-Driven", "Concise & High-Throughput", "Regulatory & Compliant"],
        key="grant_tone_select"
    )

    st.markdown("---")
    st.markdown("### 🛡️ Automated Transformation Guards")
    st.toggle("Author Guidelines Compliance Check", value=True, key="grant_guidelines_toggle")
    st.toggle("Automated Section Restructuring", value=True, key="grant_restructure_toggle")
    st.toggle("Impact Metric & Broader Context Framing", value=True, key="grant_impact_toggle")
    st.toggle("Citation Schema & Reference Mapping", value=True, key="grant_citation_map_toggle")

# ==========================================
# 3. MAIN GRANT & JOURNAL TRANSPILER WORKSPACE
# ==========================================

# Render high-performance grant and journal transpiler interface with bound parameters
render_grant_formatter_ui(
    target_profile=output_profile,
    word_constraint=word_limit,
    tone_mode=tone_adaptation
)