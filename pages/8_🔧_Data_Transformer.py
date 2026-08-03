"""
═══════════════════════════════════════════════════════════════════════════════
DATA TRANSFORMER PAGE | Advanced SPSS-Style Data Transformation Studio [v4.0]
Real-time enterprise feature engineering suite: Compute mathematical expressions, 
recode values, rank observations, bin variables, handle missing data, and track audit trails.
Designed for: Kula Chris (Chrishem)
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

# ─── PATH RESOLUTION & SETUP ─────────────────────────────────────────
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Fallback robust configurations
try:
    from modules.config import init_session_state
    from modules.ui_components import hero_card, load_css, watermark, section_header
except ImportError:
    def init_session_state():
        if "theme" not in st.session_state:
            st.session_state.theme = "dark"
    def load_css(is_dark=True):
        pass
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

st.set_page_config(
    page_title="Data Transformation Studio", 
    layout="wide", 
    page_icon="🔧",
    initial_sidebar_state="expanded"
)

init_session_state()
load_css(is_dark=st.session_state.get("theme", "dark") == "dark")

# Initialize Audit Trail History in Session State
if "transformation_audit_trail" not in st.session_state:
    st.session_state["transformation_audit_trail"] = []

# ─── HIGH-CONTRAST ENTERPRISE STYLING ────────────────────────────────
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
    "🔧 SPSS-Grade Data Transformation & Engineering Studio", 
    "High-precision feature engineering suite: Compute mathematical expressions, recode values, rank observations, bin variables, handle missing data, and run advanced transformations.", 
    "Data Transformation Engine 4.0"
)
watermark("CHRISHEM")

# ─── Dataset Acquisition & Fallback Validation ───────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ **No active dataset detected.** Please load a file in the File Analyzer or generate sample data.")
    if st.button("🔍 Generate Sample Research Cohort Data", type="primary", use_container_width=True):
        np.random.seed(42)
        demo_data = pd.DataFrame({
            "Subject_ID": [f"SUBJ_{1000 + i}" for i in range(150)],
            "Age": np.random.randint(18, 70, size=150),
            "Income_Level": np.random.normal(45000, 12000, size=150),
            "Performance_Score": np.random.uniform(50, 100, size=150),
            "Risk_Category": np.random.choice(["Low", "Medium", "High"], size=150, p=[0.5, 0.3, 0.2])
        })
        st.session_state["active_df"] = demo_data
        st.rerun()
    st.stop()

# Maintain working copy in session state to accumulate transforms
if "working_transform_df" not in st.session_state or st.session_state.get("reset_working_df", False):
    st.session_state["working_transform_df"] = active_df.copy()
    st.session_state["reset_working_df"] = False

working_df = st.session_state["working_transform_df"]

# ─── High-Level Dataset Topology Dashboard ──────────────────────────────
section_header("📊 Dataset Topology & Transformation Readiness")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("Total Rows", f"{len(working_df):,}")
with m2:
    st.metric("Total Columns", f"{len(working_df.columns):,}")
with m3:
    num_cols = len(working_df.select_dtypes(include=[np.number]).columns)
    st.metric("Numeric Variables", num_cols)
with m4:
    missing_cells = working_df.isnull().sum().sum()
    st.metric("Missing Cells", f"{missing_cells:,}")
with m5:
    memory_size = working_df.memory_usage(deep=True).sum() / (1024 * 1024)
    st.metric("Memory Footprint", f"{memory_size:.2f} MB")

with st.expander("🔍 Preview Working Dataset Schema & Descriptive Summary", expanded=False):
    st.dataframe(working_df.head(10), use_container_width=True)
    st.markdown("##### Column Data Types")
    st.write(working_df.dtypes.astype(str))

st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)

# ─── Transformation Suite Tabs Orchestration ────────────────────────────
section_header("⚙️ SPSS Transformation Workflow Studio")

transform_tabs = st.tabs([
    "⚡ Custom Compute Builder",
    "📊 Value Recode & Binning",
    "📈 Ranking & Standardization",
    "🧹 Missing Value Imputation",
    "📜 History & Audit Trail"
])

# ── TAB 1: Custom Compute Builder ───────────────────────────────────────
with transform_tabs[0]:
    st.markdown("### ⚡ Mathematical Expression Compute Engine")
    st.markdown("Construct custom numeric columns using safe pandas vector evaluation (e.g., `Income_Level * 1.15`).")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        new_col_name = st.text_input("New Variable Name", value="computed_metric")
        expression = st.text_input("Mathematical Expression", value="Income_Level / Age", help="Use exact column names and standard operators (+, -, *, /)")
    with col_c2:
        st.markdown("##### Available Columns:")
        st.code(", ".join(list(working_df.columns)), language="text")
        
    if st.button("🚀 Execute Compute Expression", type="primary"):
        try:
            # Safe evaluation using pandas dataframe eval
            working_df[new_col_name] = working_df.eval(expression)
            st.session_state["working_transform_df"] = working_df
            audit_msg = f"Computed new column '{new_col_name}' using expression: {expression}"
            st.session_state["transformation_audit_trail"].append(audit_msg)
            st.success(f"✅ Success! Column '{new_col_name}' added to working dataset.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Computation Error: {str(e)}")

# ── TAB 2: Value Recode & Binning ───────────────────────────────────────
with transform_tabs[1]:
    st.markdown("### 📊 Automated Recode & Categorical Binning")
    st.markdown("Transform continuous scales into discrete bins or categories.")
    
    numeric_columns = list(working_df.select_dtypes(include=[np.number]).columns)
    if not numeric_columns:
        st.warning("No numeric columns available for binning.")
    else:
        recode_col = st.selectbox("Select Variable to Bin", options=numeric_columns, key="recode_target")
        n_bins = st.slider("Number of Quantile Bins", min_value=2, max_value=10, value=4)
        new_bin_col = st.text_input("Binned Variable Name", value=f"{recode_col}_binned")
        
        if st.button("🚀 Generate Binned Variable", type="primary"):
            try:
                labels = [f"Tier_{i+1}" for i in range(n_bins)]
                working_df[new_bin_col] = pd.qcut(working_df[recode_col], q=n_bins, labels=labels, duplicates='drop')
                st.session_state["working_transform_df"] = working_df
                audit_msg = f"Binned variable '{recode_col}' into {n_bins} groups as '{new_bin_col}'"
                st.session_state["transformation_audit_trail"].append(audit_msg)
                st.success(f"✅ Variable '{new_bin_col}' created successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Binning Error: {str(e)}")

# ── TAB 3: Ranking & Standardization ────────────────────────────────────
with transform_tabs[2]:
    st.markdown("### 📈 Statistical Ranking & Z-Score Standardization")
    st.markdown("Convert raw numeric observations into normalized z-scores or percentile ranks.")
    
    numeric_columns = list(working_df.select_dtypes(include=[np.number]).columns)
    if not numeric_columns:
        st.warning("No numeric columns available for standardization.")
    else:
        rank_col = st.selectbox("Select Variable to Standardize/Rank", options=numeric_columns, key="rank_target")
        method = st.selectbox("Transformation Method", options=[
            "Z-Score Standardization (Mean=0, Std=1)", 
            "Min-Max Normalization (Scale 0 to 1)", 
            "Percentile Ranking"
        ])
        
        if st.button("🚀 Apply Standardization", type="primary"):
            try:
                if "Z-Score" in method:
                    mean_val = working_df[rank_col].mean()
                    std_val = working_df[rank_col].std()
                    new_col_name = f"{rank_col}_zscore"
                    working_df[new_col_name] = (working_df[rank_col] - mean_val) / (std_val if std_val != 0 else 1)
                elif "Min-Max" in method:
                    min_val = working_df[rank_col].min()
                    max_val = working_df[rank_col].max()
                    new_col_name = f"{rank_col}_minmax"
                    working_df[new_col_name] = (working_df[rank_col] - min_val) / ((max_val - min_val) if (max_val - min_val) != 0 else 1)
                else:
                    new_col_name = f"{rank_col}_percentile"
                    working_df[new_col_name] = working_df[rank_col].rank(pct=True)
                
                st.session_state["working_transform_df"] = working_df
                audit_msg = f"Applied '{method}' on variable '{rank_col}' -> '{new_col_name}'"
                st.session_state["transformation_audit_trail"].append(audit_msg)
                st.success(f"✅ Transformation complete! Created '{new_col_name}'.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Transformation Error: {str(e)}")

# ── TAB 4: Missing Value Imputation ─────────────────────────────────────
with transform_tabs[3]:
    st.markdown("### 🧹 Missing Value Imputation Suite")
    st.markdown("Automatically clean missing data points using median, mean, or constant substitution.")
    
    cols_with_missing = [c for c in working_df.columns if working_df[c].isnull().sum() > 0]
    if not cols_with_missing:
        st.info("🎉 Excellent! No missing cells detected in the active working dataset.")
    else:
        impute_col = st.selectbox("Select Column with Missing Values", options=cols_with_missing)
        impute_strategy = st.selectbox("Imputation Strategy", options=["Median", "Mean", "Mode (Most Frequent)", "Constant Zero"])
        
        if st.button("🚀 Execute Imputation", type="primary"):
            if "Median" in impute_strategy:
                val = working_df[impute_col].median()
                working_df[impute_col].fillna(val, inplace=True)
            elif "Mean" in impute_strategy:
                val = working_df[impute_col].mean()
                working_df[impute_col].fillna(val, inplace=True)
            elif "Mode" in impute_strategy:
                val = working_df[impute_col].mode()[0]
                working_df[impute_col].fillna(val, inplace=True)
            else:
                working_df[impute_col].fillna(0, inplace=True)
                
            st.session_state["working_transform_df"] = working_df
            audit_msg = f"Imputed missing cells in '{impute_col}' using {impute_strategy}"
            st.session_state["transformation_audit_trail"].append(audit_msg)
            st.success(f"✅ Missing cells in '{impute_col}' successfully imputed!")
            st.rerun()

# ── TAB 5: History & Audit Trail ────────────────────────────────────────
with transform_tabs[4]:
    st.markdown("### 📜 Transformation Audit Trail")
    st.markdown("Chronological log of all data engineering operations executed during this session.")
    
    audit_trail = st.session_state.get("transformation_audit_trail", [])
    if not audit_trail:
        st.info("No transformation steps recorded yet in this session.")
    else:
        for idx, step in enumerate(audit_trail, 1):
            st.markdown(f"**{idx}.** {step}")

# ─── Global State Persistence Bar ───────────────────────────────────────
st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)
section_header("💾 Persist Changes to Active Session")

col_save, col_reset = st.columns([3, 1])

with col_save:
    if st.button("🚀 Save Transformed Data as Active Dataset", type="primary", use_container_width=True):
        st.session_state["active_df"] = working_df.copy()
        st.success("✅ **Transformed dataset successfully saved!** Updated globally across all analytic and ML modules.")
        
        with st.expander("🔍 View Transformed Dataset Preview (First 10 Rows)", expanded=True):
            st.dataframe(working_df.head(10), use_container_width=True)

with col_reset:
    if st.button("🔄 Discard & Reset Changes", use_container_width=True):
        st.session_state["working_transform_df"] = active_df.copy()
        st.session_state["transformation_audit_trail"] = []
        st.success("🔄 Working dataset reset to original state.")
        st.rerun()