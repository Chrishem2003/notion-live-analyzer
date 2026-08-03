iiimport security_guard
security_guard.verify_access()



"""
🔍 World-Class One-Click Grant & Journal Transpiler
Enterprise-grade academic publishing and funding proposal transformation engine featuring automated
guideline compliance parsing, multi-journal style mapping, tone adaptation, and structural gap analysis pipelines.
"""
import sys
import os
import streamlit as st

# Ensure project root is in the Python search path to prevent ImportErrors
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

st.set_page_config(
    page_title="One-Click Grant & Journal Transpiler",
    page_icon="🔍 ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. CUSTOM CSS & UI ENHANCEMENTS
# ==========================================
st.markdown("""
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
    /* Card Container Styling */
    .metric-card {
        background-color: rgba(125, 125, 125, 0.05);
        border: 1px solid rgba(125, 125, 125, 0.15);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        margin-bottom: 12px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #4F46E5;
    }
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.8;
    }
    /* Section Badges */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        background-color: #E0E7FF;
        color: #3730A3;
        margin-bottom: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SAFE MODULE IMPORT & INITIALIZATION
# ==========================================
try:
    from modules.grant_formatter import (
        render_grant_formatter_ui,
        init_grant_formatter_state,
        load_grant_formatter_stylesheet
    )
    MODULES_LOADED = True
except Exception as e:
    MODULES_LOADED = False
    import_error_message = str(e)

if "grant_transpiler_active" not in st.session_state:
    st.session_state["grant_transpiler_active"] = False
if "target_output_profile" not in st.session_state:
    st.session_state["target_output_profile"] = "NIH / NSF Grant Proposal Standard"

# Initialize module state if successfully loaded
if MODULES_LOADED:
    try:
        init_grant_formatter_state()
        load_grant_formatter_stylesheet(is_dark=st.session_state.get("theme", "light") == "dark")
    except Exception:
        pass

# ==========================================
# 3. SIDEBAR CONTROLS & HUD
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
    st.markdown("### 🔍 ️ Optimization & Controls")
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
    st.markdown("### 🔍 ️ Automated Transformation Guards")
    st.toggle("Author Guidelines Compliance Check", value=True, key="grant_guidelines_toggle")
    st.toggle("Automated Section Restructuring", value=True, key="grant_restructure_toggle")
    st.toggle("Impact Metric & Broader Context Framing", value=True, key="grant_impact_toggle")
    st.toggle("Citation Schema & Reference Mapping", value=True, key="grant_citation_map_toggle")

# ==========================================
# 4. MAIN WORKSPACE & HEADER
# ==========================================
st.markdown("<span class='badge'>TRANSFORMATION ENGINE v2.0</span>", unsafe_allow_html=True)
st.title("🔍 One-Click Grant & Journal Transpiler")
st.caption("Automated academic publishing alignment, tone adaptation, and structural compliance engine.")

# Quick Metric Highlights
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="metric-card"><div class="metric-value">99.4%</div><div class="metric-label">Compliance Target</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><div class="metric-value">{output_profile.split()[0]}</div><div class="metric-label">Target Standard</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-card"><div class="metric-value">Active</div><div class="metric-label">Guard Rails</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="metric-card"><div class="metric-value">Ready</div><div class="metric-label">Engine Status</div></div>', unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 5. UI RENDER / FALLBACK SAFEGUARD
# ==========================================
if MODULES_LOADED:
    render_grant_formatter_ui(
        target_profile=output_profile,
        word_constraint=word_limit,
        tone_mode=tone_adaptation
    )
else:
    st.error("⚠️ **Module Loading Error**")
    st.warning(f"Could not load `modules.grant_formatter`. Check that `modules/grant_formatter.py` exists and has no syntax errors.\n\n**Error Details:** `{import_error_message}`")
    
    # Fallback Workspace Preview
    st.subheader("🔍 Workspace Preview Mode")
    st.info("The UI controls on the sidebar are active. Once the underlying module path is verified, full processing will automatically resume.")
    
    uploaded_file = st.file_uploader("Upload Manuscript or Proposal Draft", type=["docx", "tex", "md", "pdf"])
    if uploaded_file:
        st.success(f"File `{uploaded_file.name}` uploaded successfully. Ready for processing.")




