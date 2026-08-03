


"""
🔍 Data Transformer Page  Advanced SPSS-Style Data Transformation & Feature Engineering Studio.
"""
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Data Transformation Studio", 
    layout="wide", 
    page_icon="🔍 "
)

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header
from modules.data_transformer import render_transformer_panel

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "🔍 SPSS-Grade Data Transformation & Engineering Studio", 
    "High-precision feature engineering suite: Compute mathematical expressions, recode values, rank observations, bin variables, handle missing data, and run advanced transformations.", 
    "Data Transformation Engine 3.0"
)
watermark("CHRISHEM")

# ─── Dataset Acquisition & Fallback Validation ───────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ **No active dataset detected.** Please load a file in the File Analyzer or connect a Notion Database first.")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔍 Open File Analyzer", use_container_width=True):
            st.switch_page("pages/01_file_analyzer.py")
    with col_b:
        if st.button("🔍 Open Data Simulator", use_container_width=True):
            st.switch_page("pages/14_data_simulator.py")
    st.stop()

# ─── High-Level Dataset Topology Dashboard ──────────────────────────────
section_header("🔍 Dataset Topology & Transformation Readiness")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("🔍 Total Rows", f"{len(active_df):,}")
with m2:
    st.metric("🔍 Total Columns", f"{len(active_df.columns):,}")
with m3:
    num_cols = len(active_df.select_dtypes(include=[np.number]).columns)
    st.metric("🔍 Numeric Variables", num_cols)
with m4:
    missing_cells = active_df.isnull().sum().sum()
    st.metric("⚠️ Missing Cells", f"{missing_cells:,}")
with m5:
    memory_size = active_df.memory_usage(deep=True).sum() / (1024 * 1024)
    st.metric("🔍 Memory Footprint", f"{memory_size:.2f} MB")

with st.expander("🔍 Preview Active Dataset Schema & Descriptive Summary", expanded=False):
    st.dataframe(active_df.head(10), use_content_width=True)
    st.markdown("##### Column Data Types")
    st.write(active_df.dtypes.astype(str))

st.markdown("---")

# ─── Transformation Suite Tabs Orchestration ────────────────────────────
section_header("⚙️ SPSS Transformation Workflow Studio")

transform_tabs = st.tabs([
    "🔍 ️ Primary Transformer Panel",
    "🔍 Custom Compute Builder",
    "🔍 Value Recode & Binning",
    "🔍 Ranking & Standardization",
    "🔍 History & Undo State"
])

# ── TAB 1: Core Transformer Panel (SPSS engine wrapper) ─────────────────
with transform_tabs[0]:
    st.markdown("### 🔍 ️ Interactive SPSS Operations Hub")
    st.caption("Execute core data operations: Compute, Recode, Rank, Count, Shift, Binning, Sort, Select, Weight, and Rename.")
    
    # Render the modular transformer panel and capture transformed output
    result_df = render_transformer_panel(active_df)

# ── TAB 2: Custom Compute Builder ───────────────────────────────────────
with transform_tabs[1]:
    st.markdown("### 🔍 Mathematical Expression Compute Engine")
    st.markdown("Construct custom numeric columns using pandas/numpy inline expressions (e.g., `col_a / col_b * 100`).")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        new_col_name = st.text_input("New Variable Name", value="computed_index")
        expression = st.text_input("Mathematical Expression", value="col1  col2", help="Use standard column names and mathematical operators (, -, *, /, np.log, etc.)")
    with col_c2:
        st.markdown("##### Available Columns:")
        st.code(", ".join(list(active_df.columns)), language="text")
        
    if st.button("⚡ Execute Compute Expression", type="secondary"):
        st.info("🔍 To persist changes globally, click 'Save Transformed Data as Active Dataset' below.")

# ── TAB 3: Value Recode & Binning ───────────────────────────────────────
with transform_tabs[2]:
    st.markdown("### 🔍 Automated Recode & Categorical Binning")
    st.markdown("Transform continuous scales into discrete groups (e.g., Low, Medium, High) or remap categorical keys.")
    
    recode_col = st.selectbox("Select Variable to Recode/Bin", options=list(active_df.columns), key="recode_target")
    bin_strategy = st.radio("Binning Strategy", options=["Equal-Width Intervals (Quantization)", "Equal-Frequency Quantiles", "Custom Thresholds"])
    n_bins = st.slider("Number of Bins / Groups", min_value=2, max_value=10, value=4)

# ── TAB 4: Ranking & Standardization ────────────────────────────────────
with transform_tabs[3]:
    st.markdown("### 🔍 Statistical Ranking & Z-Score Standardization")
    st.markdown("Convert raw observations into percentiles, cumulative frequencies, or standard z-scores.")
    
    rank_col = st.selectbox("Select Variable to Rank/Standardize", options=list(active_df.columns), key="rank_target")
    standardization_method = st.selectbox("Transformation Method", options=["Z-Score Standardization (Mean=0, Std=1)", "Min-Max Normalization (0 to 1)", "Ordinal Ranking (Percentile)"])

# ── TAB 5: History & Undo State ─────────────────────────────────────────
with transform_tabs[4]:
    st.markdown("### 🔍 Transformation Audit Trail")
    st.markdown("Review applied data transformation steps during the current session.")
    st.info("🔍 No transformation history recorded yet in this session cache.")

# ─── Global State Persistence Bar ───────────────────────────────────────
st.markdown("---")
section_header("🔍 Persist Changes to Active Session")

col_save, col_reset = st.columns([3, 1])

with col_save:
    if st.button("🔍 Save Transformed Data as Active Dataset", type="primary", use_container_width=True):
        # Fallback safeguard in case result_df wasn't modified in Tab 1
        target_to_save = locals().get('result_df', active_df)
        st.session_state["active_df"] = target_to_save
        st.success("🔍 **Transformed dataset successfully saved!** Updated across all analytic modules.")
        
        with st.expander("🔍 View Transformed Dataset Preview (First 10 Rows)", expanded=True):
            st.dataframe(target_to_save.head(10), use_container_width=True)

with col_reset:
    if st.button("🔍 Discard Changes", use_container_width=True):
        st.rerun()


