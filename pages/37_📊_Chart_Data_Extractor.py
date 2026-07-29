"""
📊 Advanced Visual Chart Data Extractor & CSV Re-Synthesizer
High-performance computer vision and multimodal OCR analytics engine featuring automated
plot vectorization, axis calibration, multi-format tabular reconstruction, and robust CSV re-synthesis pipelines.
"""
import streamlit as st

st.set_page_config(
    page_title="Visual Chart Data Extractor & CSV Re-Synthesizer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

from modules.chart_data_extractor import (
    render_chart_data_extractor_ui,
    init_extractor_session_state,
    load_extractor_stylesheet
)

# Initialize secure application state and customized UI styling pipelines
init_extractor_session_state()
load_extractor_stylesheet(is_dark=st.session_state.get("theme", "light") == "dark")

# ==========================================
# 1. ADVANCED EXTRACTION ENGINE CONTROLS & HUD
# ==========================================

with st.sidebar:
    st.markdown("### ⚙️ Vision Processing Profile")
    extraction_mode = st.selectbox(
        "Extraction Engine",
        ["Deep OCR & Vector Trace", "Multimodal Vision Transformer", "High-Density Scatter Matrix", "Time-Series Auto-Grid Calibration"],
        key="extractor_engine_mode"
    )
    
    st.markdown("---")
    st.markdown("### 🎛️ Calibration & Parsing Parameters")
    confidence_threshold = st.slider("OCR Confidence Threshold (%)", 50, 99, 85, 1, key="extractor_confidence")
    interpolation_method = st.selectbox("Axis Interpolation Algorithm", ["Linear Spline", "Polynomial Fit", "Nearest Neighbor", "Bilinear Grid"], key="extractor_interpolation")
    outlier_handling = st.selectbox("Outlier Filtering Strategy", ["Strict Interquartile Range (IQR)", "Z-Score Isolation", "Manual Validation Gate", "None (Raw Re-Synthesis)"], key="extractor_outlier_mode")
    
    st.markdown("---")
    st.markdown("### 🛡️ Automated Re-Synthesis Safeguards")
    st.toggle("Auto-Detect Axis Units & Scales", value=True, key="extractor_units_toggle")
    st.toggle("Multi-Series Color Segmentation", value=True, key="extractor_segmentation_toggle")
    st.toggle("Direct CSV Schema Validation", value=True, key="extractor_schema_toggle")

# ==========================================
# 2. MAIN EXTRACTOR WORKSPACE
# ==========================================

# Render high-performance visual chart data extractor workspace with stateful parameter hooks
render_chart_data_extractor_ui(
    engine_mode=extraction_mode,
    confidence=confidence_threshold,
    interpolation=interpolation_method,
    outlier_mode=outlier_handling
)