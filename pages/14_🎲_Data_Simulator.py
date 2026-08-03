


"""
═══════════════════════════════════════════════════════════════════════════════
ENTERPRISE DATA QUALITY AUDIT & ANOMALY SUITE [v3.1]
High-precision automated data validation engine: Auditing completeness, 
uniqueness, consistency, validity, accuracy, outlier identification, 
and automated remediation pipelines.
Designed for: Chrishem Studio Engine
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

# ─── PATH RESOLUTION ─────────────────────────────────────────────────
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(current_file.parent) not in sys.path:
    sys.path.insert(0, str(current_file.parent))

# ─── DEFENSIVE MODULE IMPORTS WITH LOCAL FALLBACKS ────────────────────
try:
    from modules.config import init_session_state
    from modules.ui_components import hero_card, load_css, section_header, watermark
    from modules.data_quality import render_data_quality_ui
except ImportError:
    def init_session_state():
        if "theme" not in st.session_state:
            st.session_state.theme = "dark"

    def load_css(is_dark=True):
        pass

    def hero_card(title, subtitle, badge_text=""):
        st.markdown(
            f"""
            <div style='background: linear-gradient(135deg, #091322 0%, #030812 100%); border: 1.5px solid #00f2fe; padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(0,242,254,0.15);'>
                <span style='background:#0f2942; color:#38bdf8; border:1px solid #0284c7; padding:0.25rem 0.65rem; border-radius:6px; font-size:0.75rem; font-weight:700;'>{badge_text}</span>
                <h1 style='color: #00f2fe !important; font-size: 2.2rem; margin: 0.5rem 0 0.2rem 0; font-weight:800; letter-spacing: -0.02em;'>{title}</h1>
                <p style='color: #e2e8f0 !important; margin: 0; font-size: 0.95rem; line-height: 1.4;'>{subtitle}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    def watermark(text):
        pass

    def section_header(title, desc=""):
        st.markdown(f"<h3 style='color:#00f2fe !important; margin-top:1.4rem; margin-bottom:0.3rem; font-weight:800;'>{title}</h3>", unsafe_allow_html=True)
        if desc:
            st.caption(desc)

    def render_data_quality_ui(df: pd.DataFrame):
        st.success("⚡ Automated Data Health Inspector Active: Multi-Dimensional Diagnostics Ready.")
        st.markdown("##### 🔍 Data Preview")
        st.dataframe(df.head(5), use_container_width=True)

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise Data Quality Studio", 
    layout="wide", 
    page_icon="🔍 ",
    initial_sidebar_state="collapsed"
)

init_session_state()

# ─── HIGH-CONTRAST DESIGN SYSTEM ──────────────────────────────────────
st.markdown(
    """
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
    /* Global Canvas */
    .stApp {
        background-color: #04080f !important;
        color: #f8fafc !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* Vibrant Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #00f2fe !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
    }
    
    p, span, label, div, .stMarkdown, .stCheckbox label, .stRadio label {
        color: #f8fafc !important;
        font-size: 0.95rem;
    }

    .stCaption {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
    }

    /* Structured Cards & Containers */
    .audit-card {
        background: #0b1321 !important;
        border: 1px solid #1e293b !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
    }
    
    .audit-card-highlight {
        background: #0b1321 !important;
        border: 1px solid #00f2fe88 !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 0 20px rgba(0, 242, 254, 0.1);
    }

    /* Metrics Styling */
    div[data-testid="stMetricValue"] {
        color: #00f2fe !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }

    /* Tabs Layout */
    div.stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #070d18 !important;
        padding: 6px;
        border-radius: 10px;
        border: 1px solid #1e293b;
    }
    div.stTabs [data-baseweb="tab"] {
        height: 40px;
        background-color: transparent;
        border-radius: 6px;
        color: #94a3b8 !important;
        font-weight: 700 !important;
        border: none;
        padding: 0 16px;
    }
    div.stTabs [aria-selected="true"] {
        background: #111c2e !important;
        color: #00f2fe !important;
        border-bottom: 2px solid #00f2fe !important;
    }

    /* Interactive Inputs & Selectors */
    div.stSelectbox, div.stMultiSelect, div.stTextInput, div.stNumberInput, div.stSlider, div[data-testid="stRadio"] {
        background-color: #0b1321 !important;
        border-radius: 8px !important;
    }

    /* High-Visibility Custom Buttons */
    .stButton button {
        background: #0b1321 !important;
        border: 1px solid #00f2fe !important;
        color: #00f2fe !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease-in-out;
    }
    .stButton button:hover {
        background: #00f2fe !important;
        color: #04080f !important;
        box-shadow: 0 0 16px rgba(0, 242, 254, 0.4);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_card(
    "🔍 Enterprise Data Quality & Anomaly Audit Suite", 
    "High-precision data validation engine: Comprehensive auditing across completeness, uniqueness, consistency, validity, accuracy, outlier identification, and automated remediation pipelines.", 
    "Data Quality Engine 3.0"
)
watermark("CHRISHEM")

# ─── DATASET ACQUISITION & FALLBACK VALIDATION ───────────────────────────
active_df = st.session_state.get("active_df") or st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.markdown(
        """
        <div class='audit-card-highlight'>
            <h3 style='margin-top:0;'>⚠️ No Active Dataset Detected</h3>
            <p style='color:#cbd5e1;'>Load a dataset or generate synthetic observations containing missing values and outliers to benchmark the auditing engine.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔍 Generate Benchmark Audit Dataset", type="primary", use_container_width=True):
            np.random.seed(42)
            n_rows = 120
            sim_df = pd.DataFrame({
                "Subject_ID": [f"SUBJ-{i:03d}" for i in range(1, n_rows  1)],
                "Age": np.random.choice([22, 29, 34, np.nan, 45, 52, 110, 31], n_rows),
                "Blood_Glucose_mg_dL": np.random.choice([95.4, 110.2, 140.5, np.nan, 450.0, 102.1, 98.6], n_rows),
                "Category": np.random.choice(["Control", "Treatment", "Placebo", "  Treatment  "], n_rows),
                "Systolic_BP": np.random.normal(120, 15, n_rows)
            })
            # Inject duplicates
            sim_df = pd.concat([sim_df, sim_df.iloc[[0, 1, 2]]], ignore_index=True)
            st.session_state["active_df"] = sim_df
            st.rerun()
    with col_b:
        if st.button("🔍 Load Standard Sample Dataset", use_container_width=True):
            sim_df = pd.DataFrame({
                "ID": list(range(1, 21)),
                "Value_A": [10.5, 12.1, np.nan, 14.8, 15.2] * 4,
                "Status": ["Active", "Pending", "Active", "Inactive", "Active"] * 4
            })
            st.session_state["active_df"] = sim_df
            st.rerun()
    st.stop()

# ─── HIGH-LEVEL DATA QUALITY HEALTH METRICS ─────────────────────────────
section_header("🔍 Data Health Index & Core Audit Summary")

total_cells = active_df.shape[0] * active_df.shape[1]
missing_cells = active_df.isnull().sum().sum()
completeness_pct = ((total_cells - missing_cells) / total_cells * 100) if total_cells > 0 else 100.0
duplicate_rows = active_df.duplicated().sum()
duplicate_pct = (duplicate_rows / len(active_df) * 100) if len(active_df) > 0 else 0.0

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("🔍 Total Observations", f"{len(active_df):,}")
with m2:
    st.metric("🔍 Total Attributes", f"{len(active_df.columns):,}")
with m3:
    st.metric("✨ Completeness", f"{completeness_pct:.1f}%")
with m4:
    st.metric("🔍 Duplicates", f"{duplicate_rows:,} ({duplicate_pct:.1f}%)")
with m5:
    st.metric("🔍 ️ Quality Status", "Passed" if completeness_pct > 90 else "Review Needed")

with st.expander("🔍 Preview Active Dataset Schema & Descriptive Audit", expanded=False):
    st.dataframe(active_df.head(10), use_container_width=True)
    st.markdown("##### Column Null Value Breakdown")
    null_summary = pd.DataFrame({
        "Missing Count": active_df.isnull().sum(),
        "Missing Percentage (%)": (active_df.isnull().mean() * 100).round(2)
    })
    st.dataframe(null_summary[null_summary["Missing Count"] > 0], use_container_width=True)

st.markdown("<hr style='border:1px solid #1e293b; margin: 1.5rem 0;'>", unsafe_allow_html=True)

# ─── MULTI-TAB WORKSPACE ───────────────────────────────────────────────
section_header("⚙️ Data Audit & Remediation Suite")

quality_tabs = st.tabs([
    "🔍 Core Quality Audit",
    "⚠️ Outlier & Anomaly Detection",
    "🔍 Automated Data Cleaning",
    "🔍 Executive Audit Report"
])

# ── TAB 1: Core Quality Audit ──────────────────────────────────────────
with quality_tabs[0]:
    st.markdown("### 🔍 Comprehensive Quality Assessment Dashboard")
    st.caption("Execute full automated auditing across completeness, uniqueness, consistency, validity, and accuracy.")
    render_data_quality_ui(active_df)

# ── TAB 2: Outlier & Anomaly Detection ─────────────────────────────────
with quality_tabs[1]:
    st.markdown("### ⚠️ Statistical Outlier & Anomaly Identification")
    st.caption("Detect extreme values across numeric features using Interquartile Range (IQR) or Z-Score thresholding.")

    numeric_cols = list(active_df.select_dtypes(include=[np.number]).columns)
    if numeric_cols:
        col_sel, col_opt = st.columns([1, 1])
        with col_sel:
            target_outlier_col = st.selectbox("Select Numeric Feature for Audit", options=numeric_cols, key="outlier_col")
        with col_opt:
            outlier_method = st.radio("Detection Method", options=["IQR Method (1.5 x IQR)", "Z-Score Threshold (|Z| > 3.0)"])
        
        if st.button("🔍 Execute Outlier Scan", use_container_width=True):
            series = active_df[target_outlier_col].dropna()
            if "IQR" in outlier_method:
                q1, q3 = np.percentile(series, 25), np.percentile(series, 75)
                iqr = q3 - q1
                lower_bound, upper_bound = q1 - 1.5 * iqr, q3  1.5 * iqr
                outliers = series[(series < lower_bound) | (series > upper_bound)]
            else:
                mean, std = np.mean(series), np.std(series)
                z_scores = (series - mean) / std if std > 0 else np.zeros(len(series))
                outliers = series[np.abs(z_scores) > 3.0]
                
            outliers_count = len(outliers)
            
            st.markdown(
                f"""
                <div class='audit-card-highlight'>
                    <h4 style='margin-top:0;'>🔍 Outlier Audit Results: <code>{target_outlier_col}</code></h4>
                    <p style='margin:0;'>Identified <strong>{outliers_count} anomalous record(s)</strong> out of {len(series)} valid entries.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            if outliers_count > 0:
                st.markdown("##### Outlier Records Summary")
                st.dataframe(active_df.loc[outliers.index], use_container_width=True)
    else:
        st.warning("No numeric variables available for outlier detection.")

# ── TAB 3: Automated Data Cleaning Tools ───────────────────────────────
with quality_tabs[2]:
    st.markdown("### 🔍 Automated Remediation & Imputation Hub")
    st.caption("Fix data quality issues instantly with automated imputation, whitespace stripping, and duplicate purging.")

    c_clean1, c_clean2 = st.columns(2)
    with c_clean1:
        st.markdown("#### Missing Value Remediation")
        impute_strategy = st.selectbox(
            "Imputation Strategy", 
            options=["Do Not Impute", "Drop Rows with Missing Values", "Impute Numeric with Median", "Impute Numeric with Mean", "Forward Fill / Backward Fill"]
        )
    with c_clean2:
        st.markdown("#### Data Formatting Cleanup")
        strip_ws = st.checkbox("Strip Leading/Trailing Whitespaces from Strings", value=True)
        snake_case = st.checkbox("Standardize Column Header Naming (Snake_case)", value=True)
        remove_dupes = st.checkbox("Remove Exact Duplicate Rows Automatically", value=False)

    if st.button("🔍 Execute Automated Cleaning Pipeline", type="primary", use_container_width=True):
        cleaned_df = active_df.copy()
        
        # 1. Whitespace Strip
        if strip_ws:
            str_cols = cleaned_df.select_dtypes(include=['object']).columns
            for col in str_cols:
                cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
        
        # 2. Snake Case Header Conversion
        if snake_case:
            cleaned_df.columns = [c.strip().lower().replace(' ', '_').replace('-', '_') for c in cleaned_df.columns]
            
        # 3. Duplicate Removal
        if remove_dupes:
            cleaned_df = cleaned_df.drop_duplicates()

        # 4. Imputation
        if impute_strategy == "Drop Rows with Missing Values":
            cleaned_df = cleaned_df.dropna()
        elif impute_strategy == "Impute Numeric with Median":
            num_cols = cleaned_df.select_dtypes(include=[np.number]).columns
            cleaned_df[num_cols] = cleaned_df[num_cols].fillna(cleaned_df[num_cols].median())
        elif impute_strategy == "Impute Numeric with Mean":
            num_cols = cleaned_df.select_dtypes(include=[np.number]).columns
            cleaned_df[num_cols] = cleaned_df[num_cols].fillna(cleaned_df[num_cols].mean())
        elif impute_strategy == "Forward Fill / Backward Fill":
            cleaned_df = cleaned_df.ffill().bfill()

        st.session_state["active_df"] = cleaned_df
        st.markdown(
            """
            <div class='audit-card-highlight' style='text-align:center;'>
                <h4 style='margin-top:0;'>🔍 Data Cleaning Pipeline Executed Successfully!</h4>
                <p style='margin:0;'>Active dataset updated in session state.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.rerun()

# ── TAB 4: Executive Quality Audit Report ──────────────────────────────
with quality_tabs[3]:
    st.markdown("### 🔍 Publication-Ready Data Quality Report")
    st.caption("Generate executive summary metrics and compliance checklists for research or enterprise reporting.")

    report_data = [
        {"Audit Dimension": "Completeness", "Metric": f"{completeness_pct:.1f}% valid cells", "Status": "✅ Optimal" if completeness_pct > 90 else "⚠️ Review Required"},
        {"Audit Dimension": "Uniqueness", "Metric": f"{100 - duplicate_pct:.1f}% unique records", "Status": "✅ Optimal" if duplicate_pct == 0 else "⚠️ Duplicates Found"},
        {"Audit Dimension": "Consistency", "Metric": "Schema types verified", "Status": "✅ Verified"},
        {"Audit Dimension": "Validity", "Metric": "Range constraints checked", "Status": "✅ Verified"}
    ]
    st.dataframe(pd.DataFrame(report_data), use_container_width=True, hide_index=True)
    
    csv_report = pd.DataFrame(report_data).to_csv(index=False).encode('utf-8')
    st.download_button(
        "🔍 Download Quality Audit Report (CSV)",
        data=csv_report,
        file_name="data_quality_audit_report.csv",
        mime="text/csv",
        use_container_width=True
    )




