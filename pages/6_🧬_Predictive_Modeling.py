"""
═══════════════════════════════════════════════════════════════════════════════
GENOMIC & ENTERPRISE PREDICTIVE MODELING / AUTOML SUITE [v4.0 ENTERPRISE]
Production-grade machine learning engine featuring live scikit-learn model training,
automated imputation, metric evaluation, and diagnostic visualization.
Designed for: Kula Chris (Chrishem)
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

# Scikit-Learn Machine Learning Imports
try:
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.impute import SimpleImputer
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.linear_model import LogisticRegression, LinearRegression
    from sklearn.metrics import accuracy_score, classification_report, mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# ─── PATH RESOLUTION ─────────────────────────────────────────────────
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(current_file.parent) not in sys.path:
    sys.path.insert(0, str(current_file.parent))

# Fallback robust implementations for modular imports
try:
    from modules.config import init_session_state
    from modules.ui_components import hero_card, load_css, section_header, watermark
except ImportError:
    def init_session_state():
        if "theme" not in st.session_state:
            st.session_state.theme = "dark"

    def hero_card(title, subtitle, badge_text=""):
        st.markdown(
            f"""
            <div style='background: linear-gradient(135deg, #0b1e36 0%, #061527 100%); border: 2px solid #00f2fe; padding: 1.5rem; border-radius: 14px; margin-bottom: 1.5rem;'>
                <span class='badge-primary'>{badge_text}</span>
                <h1 style='color: #00f2fe; font-size: 2.2rem; margin: 0.4rem 0 0.2rem 0; font-weight:800;'>{title}</h1>
                <p style='color: #cbd5e1; margin: 0; font-size: 0.95rem;'>{subtitle}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    def watermark(text):
        pass

    def section_header(title, desc=""):
        st.markdown(f"<h3 style='color:#00f2fe; margin-top:1.2rem; margin-bottom:0.3rem;'>{title}</h3>", unsafe_allow_html=True)
        if desc:
            st.caption(desc)

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Advanced Predictive Modeling", 
    layout="wide", 
    page_icon="🔍",
    initial_sidebar_state="expanded"
)

init_session_state()

# ─── HIGH-CONTRAST CUSTOM STYLING ENGINE ─────────────────────────────
st.markdown(
    """
    <style>
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }
    .stApp {
        background-color: #060b13 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #00f2fe !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }
    p, span, label, div, .stMarkdown, .stCaption {
        color: #f8fafc !important;
        font-size: 0.95rem;
    }
    .contrast-card {
        background: #111c2e !important;
        border: 1px solid #00f2fe44 !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    div[data-testid="stMetricValue"] {
        color: #00f2fe !important;
        font-size: 1.8rem !important;
        font-weight: 900 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 0.75rem;
    }
    .badge-primary {
        background: #172554;
        color: #93c5fd;
        border: 1px solid #1d4ed8;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-size: 0.7rem;
        font-family: monospace;
        letter-spacing: 0.05em;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_card(
    "🔍 Enterprise Predictive Modeling & AutoML Suite",
    "Production-ready automated machine learning pipelines: Live training, feature scaling, model benchmarking, and performance evaluation.",
    "AutoML Engine 4.0"
)
watermark("CHRISHEM")

if not SKLEARN_AVAILABLE:
    st.error("⚠️ `scikit-learn` is required for this module. Please ensure it is installed in your python environment.")
    st.stop()

# ── Data Acquisition & Fallback Validation ───────────────────────────
active_df = st.session_state.get("active_df") or st.session_state.get("working_df") or st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.markdown(
        """
        <div class='contrast-card'>
            <h3 style='margin-top:0;'>⚠️ No Active Dataset Detected</h3>
            <p style='color:#cbd5e1;'>Load a research dataset or generate synthetic observations below to power the machine learning pipeline.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔍 Load Synthetic Binary Classification Dataset", type="primary", use_container_width=True):
            np.random.seed(42)
            sim_df = pd.DataFrame({
                "Gene_Expression_A": np.random.normal(12.5, 2.1, 150),
                "Gene_Expression_B": np.random.normal(8.3, 1.4, 150),
                "Protein_Density": np.random.uniform(0.1, 5.0, 150),
                "Patient_Age": np.random.randint(22, 78, 150),
                "Treatment_Response": np.random.choice([0, 1], p=[0.4, 0.6], size=150)
            })
            st.session_state["active_df"] = sim_df
            st.session_state["working_df"] = sim_df
            st.rerun()
    with col_b:
        if st.button("🔍 Load Synthetic Regression Dataset", use_container_width=True):
            np.random.seed(101)
            x1 = np.random.randn(150)
            x2 = np.random.randn(150)
            y = 3.5 * x1 - 2.0 * x2 + np.random.normal(0, 0.5, 150)
            sim_df = pd.DataFrame({
                "Predictor_X1": x1,
                "Predictor_X2": x2,
                "Environmental_Factor": np.random.uniform(10, 50, 150),
                "Target_Continuous_Score": y
            })
            st.session_state["active_df"] = sim_df
            st.session_state["working_df"] = sim_df
            st.rerun()
    st.stop()

# ── Dataset Topology Metrics ────────────────────────────────────────
section_header("🔍 Dataset Topology & ML Readiness")

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Total Observations", f"{len(active_df):,}")
with m2:
    st.metric("Total Features", f"{len(active_df.columns):,}")
with m3:
    numeric_cols_count = len(active_df.select_dtypes(include=[np.number]).columns)
    st.metric("Numeric Predictors", numeric_cols_count)
with m4:
    missing_cells_pct = (active_df.isnull().sum().sum() / (active_df.shape[0] * active_df.shape[1])) * 100
    st.metric("Missing Data Density", f"{missing_cells_pct:.1f}%")

with st.expander("🔍 Preview Active Dataset Schema", expanded=False):
    st.dataframe(active_df.head(10), use_container_width=True)

st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)

# ── Real Functional Machine Learning Training Engine ──────────────────
section_header("⚙️ Live Model Training & Execution Suite")

target_var = st.selectbox("🔍 Select Target Variable to Predict", options=active_df.columns, index=len(active_df.columns)-1)
feature_cols = [c for c in active_df.columns if c != target_var]
selected_features = st.multiselect("🔍 Select Feature Predictors", options=feature_cols, default=feature_cols)

col_cfg1, col_cfg2 = st.columns(2)
with col_cfg1:
    test_size_pct = st.slider("Test Set Split Proportion (%)", min_value=10, max_value=50, value=20, step=5)
with col_cfg2:
    model_type = st.radio("Task Category", options=["Classification", "Regression"], horizontal=True)

if st.button("🚀 Train and Evaluate Model Live", type="primary", use_container_width=True):
    if not selected_features:
        st.error("Please select at least one feature predictor.")
    else:
        with st.spinner("Preprocessing data, imputing missing values, and fitting models..."):
            try:
                X = active_df[selected_features].copy()
                y = active_df[target_var].copy()

                # Handle missing values in numeric columns
                imputer = SimpleImputer(strategy="median")
                X_imputed = pd.DataFrame(imputer.fit_transform(X), columns=selected_features)

                if model_type == "Classification":
                    # Encode target if non-numeric
                    if y.dtype == 'object' or y.dtype.name == 'category':
                        le = LabelEncoder()
                        y_encoded = le.fit_transform(y.astype(str))
                    else:
                        y_encoded = y.values

                    X_train, X_test, y_train, y_test = train_test_split(
                        X_imputed, y_encoded, test_size=(test_size_pct / 100.0), random_state=42
                    )

                    scaler = StandardScaler()
                    X_train_scaled = scaler.fit_transform(X_train)
                    X_test_scaled = scaler.transform(X_test)

                    rf = RandomForestClassifier(random_state=42)
                    rf.fit(X_train_scaled, y_train)
                    y_pred_rf = rf.predict(X_test_scaled)
                    acc_rf = accuracy_score(y_test, y_pred_rf)

                    lr = LogisticRegression(max_iter=500, random_state=42)
                    lr.fit(X_train_scaled, y_train)
                    y_pred_lr = lr.predict(X_test_scaled)
                    acc_lr = accuracy_score(y_test, y_pred_lr)

                    st.success("✅ Classification Models Trained Successfully!")
                    
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        st.metric("Random Forest Accuracy", f"{acc_rf * 100:.2f}%")
                    with col_m2:
                        st.metric("Logistic Regression Accuracy", f"{acc_lr * 100:.2f}%")

                    st.markdown("#### Feature Importance (Random Forest)")
                    importances = pd.Series(rf.feature_importances_, index=selected_features).sort_values(ascending=False)
                    st.bar_chart(importances)

                else:
                    # Regression Task
                    y_numeric = pd.to_numeric(y, errors='coerce')
                    valid_idx = y_numeric.notnull()
                    X_reg = X_imputed.loc[valid_idx]
                    y_reg = y_numeric.loc[valid_idx]

                    X_train, X_test, y_train, y_test = train_test_split(
                        X_reg, y_reg, test_size=(test_size_pct / 100.0), random_state=42
                    )

                    scaler = StandardScaler()
                    X_train_scaled = scaler.fit_transform(X_train)
                    X_test_scaled = scaler.transform(X_test)

                    rf_reg = RandomForestRegressor(random_state=42)
                    rf_reg.fit(X_train_scaled, y_train)
                    y_pred_rf = rf_reg.predict(X_test_scaled)
                    r2_rf = r2_score(y_test, y_pred_rf)
                    rmse_rf = np.sqrt(mean_squared_error(y_test, y_pred_rf))

                    lin_reg = LinearRegression()
                    lin_reg.fit(X_train_scaled, y_train)
                    y_pred_lin = lin_reg.predict(X_test_scaled)
                    r2_lin = r2_score(y_test, y_pred_lin)
                    rmse_lin = np.sqrt(mean_squared_error(y_test, y_pred_lin))

                    st.success("✅ Regression Models Trained Successfully!")

                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        st.metric("Random Forest R² Score", f"{r2_rf:.4f}")
                        st.metric("Random Forest RMSE", f"{rmse_rf:.4f}")
                    with col_r2:
                        st.metric("Linear Regression R² Score", f"{r2_lin:.4f}")
                        st.metric("Linear Regression RMSE", f"{rmse_lin:.4f}")

            except Exception as e:
                st.error(f"Error during model training execution: {str(e)}")