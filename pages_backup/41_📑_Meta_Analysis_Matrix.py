import security_guard
security_guard.verify_access()



"""
🔍 World-Class Multi-Paper Meta-Analysis Matrix Synthesizer
Enterprise-grade systematic review and evidence synthesis engine featuring automated effect-size extraction,
heterogeneity modeling ($I^2$, Cochran's Q), publication bias Egger's regression testing, and forest plot generation pipelines.
"""
import sys
import os
import streamlit as st

# ==========================================
# 0. DYNAMIC PATH RESOLUTION (PREVENT IMPORT ERRORS)
# ==========================================
# Appends project root directory to sys.path to ensure module imports are detected
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

st.set_page_config(
    page_title="Multi-Paper Meta-Analysis Matrix Synthesizer",
    page_icon="🔍 ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. ADVANCED UI & STYLING PIPELINE
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
    /* Gradient Badges & Accent Containers */
    .meta-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 16px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: #FFFFFF;
        margin-bottom: 12px;
    }
    
    /* Interactive Metric Cards */
    .meta-card {
        background-color: rgba(16, 185, 129, 0.04);
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .meta-card:hover {
        border-color: rgba(16, 185, 129, 0.45);
        transform: translateY(-2px);
    }
    .meta-card-value {
        font-size: 1.7rem;
        font-weight: 800;
        background: linear-gradient(135deg, #059669, #10B981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .meta-card-label {
        font-size: 0.8rem;
        font-weight: 600;
        opacity: 0.75;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. META-ANALYSIS SESSION STATE & SAFE IMPORT
# ==========================================
if "meta_matrix_active" not in st.session_state:
    st.session_state["meta_matrix_active"] = False
if "meta_model_type" not in st.session_state:
    st.session_state["meta_model_type"] = "Random-Effects Model (DerSimonian-Laird)"

MODULES_LOADED = False
import_error_msg = ""

try:
    from modules.meta_analysis_matrix import (
        render_meta_analysis_matrix_ui,
        init_meta_matrix_state,
        load_meta_matrix_stylesheet
    )
    MODULES_LOADED = True
except Exception as e:
    import_error_msg = str(e)

# Safe state and stylesheet initialization
if MODULES_LOADED:
    try:
        init_meta_matrix_state()
        load_meta_matrix_stylesheet(is_dark=st.session_state.get("theme", "light") == "dark")
    except Exception:
        pass

# ==========================================
# 3. SYNTHESIS CONTROL HUD & PARAMETERS
# ==========================================

with st.sidebar:
    st.markdown("### ⚙️ Statistical Synthesis Model")
    model_type = st.selectbox(
        "Pooling Architecture",
        [
            "Random-Effects Model (DerSimonian-Laird)",
            "Fixed-Effect Model (Mantel-Haenszel / Peto)",
            "Bayesian Hierarchical Meta-Analysis",
            "Multivariate Meta-Regression"
        ],
        key="meta_model_type_select"
    )
    st.session_state["meta_model_type"] = model_type

    st.markdown("---")
    st.markdown("### 🔍 Effect Size & Metric Parameters")
    effect_metric = st.selectbox(
        "Primary Effect Metric",
        ["Odds Ratio (OR)", "Relative Risk (RR)", "Risk Difference (RD)", "Standardized Mean Difference (SMD)", "Pearson's Correlation (r)"],
        key="meta_effect_metric"
    )
    confidence_level = st.slider("Confidence Interval (%)", 90, 99, 95, 1, key="meta_confidence_level")

    st.markdown("---")
    st.markdown("### 🔍 ️ Bias Detection & Heterogeneity")
    eggers_opt = st.toggle("Egger's Test for Publication Bias", value=True, key="meta_eggers_toggle")
    st.toggle("Fail-Safe N Calculation (Rosenthal)", value=True, key="meta_failsafe_toggle")
    st.toggle("Leave-One-Out Sensitivity Analysis", value=True, key="meta_sensitivity_toggle")
    st.toggle("Trim-and-Fill Imputation", value=True, key="meta_trimfill_toggle")

# ==========================================
# 4. MAIN META-ANALYSIS MATRIX WORKSPACE
# ==========================================

st.markdown("<span class='meta-badge'>SYNTHESIS ENGINE v2.5</span>", unsafe_allow_html=True)
st.title("🔍 Multi-Paper Meta-Analysis Matrix Synthesizer")
st.caption("Automated systematic review, effect-size extraction, heterogeneity modeling, and publication bias analytics.")

# Strategic Metric Highlights
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="meta-card"><div class="meta-card-value">{effect_metric.split()[0]}</div><div class="meta-card-label">Effect Metric</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="meta-card"><div class="meta-card-value">{confidence_level}%</div><div class="meta-card-label">Confidence Interval</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="meta-card"><div class="meta-card-value">{"Active" if eggers_opt else "Inactive"}</div><div class="meta-card-label">Egger\'s Bias Test</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="meta-card"><div class="meta-card-value">Ready</div><div class="meta-card-label">Engine Status</div></div>', unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 5. WORKSPACE RENDER / NATIVE FALLBACK
# ==========================================

if MODULES_LOADED:
    render_meta_analysis_matrix_ui(
        model_type=model_type,
        effect_metric=effect_metric,
        confidence_level=confidence_level
    )
else:
    st.error("⚠️ **Module Resolution Error**")
    st.info(f"The module `modules.meta_analysis_matrix` could not be loaded directly. Reverting to **Native Workspace Mode**.\n\n`Error Details: {import_error_msg}`")
    
    st.subheader("🔍 Synthesis Matrix Preview")
    
    # Native Matrix Preview Mock Data
    sample_data = {
        "Study Name": ["Alpha et al. (2021)", "Beta et al. (2022)", "Gamma et al. (2023)", "Delta et al. (2024)"],
        "Sample Size (N)": [150, 320, 210, 450],
        f"Effect Size ({effect_metric.split()[0]})": [1.25, 0.88, 1.45, 1.10],
        "Lower CI": [1.05, 0.72, 1.15, 0.95],
        "Upper CI": [1.48, 1.08, 1.82, 1.28],
        "Weight (%)": ["18.5%", "32.1%", "21.4%", "28.0%"]
    }
    
    st.dataframe(sample_data, use_container_width=True)
    st.success("✅ Path guard applied. Create `modules/meta_analysis_matrix.py` in your root repository to link full backend execution.")



