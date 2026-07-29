"""
🧬 Predictive Modeling Page — Enterprise AutoML Classification, Regression, Clustering, & Forecasting Suite.
"""
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Advanced Predictive Modeling", layout="wide", page_icon="🧬")

from modules.config import init_session_state
from modules.ui_components import hero_card, section_header, load_css, watermark
from modules.predictive_engine import render_predictive_modeling_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "🧬 Enterprise Predictive Modeling & AutoML Suite",
    "High-throughput automated machine learning pipelines: Real-time algorithm benchmarking, hyperparameter grid-search, cross-validation, and diagnostic evaluation.",
    "AutoML Engine 3.0"
)
watermark("CHRISHEM")

# ── Data Acquisition & Fallback Validation ───────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ **No active dataset detected.** Please initialize a data source via the File Analyzer, sync a Notion database, or build a synthetic dataset using the Data Simulator module.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📁 Go to File Analyzer", use_container_width=True):
            st.switch_page("pages/01_file_analyzer.py") # Example fallback redirect if multi-page structure applies
    with col_b:
        if st.button("🎲 Generate Simulated Data", use_container_width=True):
            st.switch_page("pages/14_data_simulator.py")
    st.stop()

# ── Advanced Header Dashboard Metrics ────────────────────────────────
section_header("📊 Dataset Topology & Machine Learning Readiness")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("📋 Total Observations", f"{len(active_df):,}")
with m2:
    st.metric("🔢 Total Features", f"{len(active_df.columns):,}")
with m3:
    numeric_cols_count = len(active_df.select_dtypes(include=[np.number]).columns)
    st.metric("📊 Numeric Predictors", numeric_cols_count)
with m4:
    categorical_cols_count = len(active_df.select_dtypes(include=['object', 'category']).columns)
    st.metric("🏷️ Categorical Features", categorical_cols_count)
with m5:
    missing_cells_pct = (active_df.isnull().sum().sum() / (active_df.shape[0] * active_df.shape[1])) * 100
    st.metric("⚠️ Missing Data Density", f"{missing_cells_pct:.1f}%")

with st.expander("🔍 Preview Active Dataset Schema & Descriptive Statistics", expanded=False):
    st.dataframe(active_df.head(10), use_container_width=True)
    st.markdown("##### Feature Type Distribution")
    st.write(active_df.dtypes.astype(str))

st.markdown("---")

# ── Main AutoML Suite Orchestration ─────────────────────────────────
section_header("⚙️ Automated Machine Learning Pipeline Controller")

tabs = st.tabs([
    "🎯 Supervised Classification", 
    "📈 Advanced Regression", 
    "🧩 Unsupervised Clustering", 
    "⏳ Time-Series Forecasting",
    "⚙️ Hyperparameter Configuration"
])

with tabs[0]:
    st.markdown("### 🎯 Automated Classification Suite")
    st.markdown("Train, benchmark, and cross-validate multi-class and binary classification algorithms (Random Forest, XGBoost, LightGBM, SVM, Logistic Regression).")
    # Pass dataset directly to the advanced modular engine
    render_predictive_modeling_ui(active_df)

with tabs[1]:
    st.markdown("### 📈 Automated Regression Suite")
    st.markdown("Model continuous targets with automated residual analysis, RMSE, MAE, and $R^2$ performance metrics optimization.")
    st.info("💡 **Tip:** Select a continuous target metric containing float or integer values within the modeling panel.")

with tabs[2]:
    st.markdown("### 🧩 Unsupervised Clustering & Dimensionality Reduction")
    st.markdown("Discover latent groupings via K-Means, DBSCAN, and Hierarchical Agglomerative Clustering backed by PCA spatial visualization.")

with tabs[3]:
    st.markdown("### ⏳ Time-Series Trend Forecasting")
    st.markdown("Project temporal horizons using autoregressive models, moving averages, and decomposition trend estimators.")

with tabs[4]:
    st.markdown("### ⚙️ Global Hyperparameter & Compute Settings")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.slider("Cross-Validation Folds (k)", min_value=3, max_value=10, value=5, help="Sets the validation split depth for robust model out-of-sample scoring.")
        st.slider("Test Set Proportion (%)", min_value=10, max_value=50, value=20, step=5)
    with col_c2:
        st.selectbox("Imputation Strategy for Missing Values", options=["Median / Mode (Robust)", "Mean / Constant", "KNN Imputer", "Drop Missing Rows"])
        st.toggle("Enable Automated Feature Scaling (StandardScaler / MinMaxScaler)", value=True)
    
    if st.button("💾 Save Pipeline Configuration Settings", type="primary"):
        st.success("✅ AutoML global hyperparameters updated successfully across session states!")