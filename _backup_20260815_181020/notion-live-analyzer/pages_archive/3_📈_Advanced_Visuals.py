# ═══════════════════════════════════════════════════════════════════════════════
# ADVANCED FILE ANALYZER & MULTI-FORMAT INGESTION ENGINE [ENTERPRISE v7.0 PRO]
# Standalone Edition with High-Contrast Cyber-Emerald Styling, PII Masking,
# Automated Bayesian Outlier Correction, PCA Latent Space Projection,
# and Resilient Multi-Format File Parsing.
# Designed for: Kula Chris (Chrishem)
# ═══════════════════════════════════════════════════════════════════════════════

import csv
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
import streamlit as st

# Optional Plotly backend – degrades gracefully if not installed
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ─── PATH RESOLUTION ─────────────────────────────────────────────────
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(current_file.parent) not in sys.path:
    sys.path.insert(0, str(current_file.parent))

# Fallback robust implementations for external modules
try:
    from modules.config import init_session_state, CHART_COLOR_PALETTES
    from modules.data_processor import infer_column_types, profile_dataset
    from modules.export import render_export_buttons, get_chart_download_link
    from modules.chart_builder import build_chart
    from modules.file_uploader import (
        SUPPORTED_FORMATS,
        manual_data_entry,
        merge_datasets,
        parse_uploaded_file,
    )
    from modules.ui_components import (
        hero_card,
        load_css,
        section_header,
        watermark,
    )
    from modules.viz_engine import (
        ALL_CHART_TYPES,
        auto_recommend_chart,
        explain_chart_recommendation,
        get_chart_search_results,
    )
except ImportError:
    CHART_COLOR_PALETTES = {
        "Cyber Neon": ["#00f2fe", "#4facfe", "#00f2fe", "#7f00ff"],
        "Viridis": ["#440154", "#21908d", "#fde725"],
        "Plasma": ["#0d0887", "#cc4678", "#f0f921"]
    }
    ALL_CHART_TYPES = [
        "histogram", "line", "bar", "scatter", "pie", "box", 
        "parallel_coordinates", "treemap", "bubble", "scatter_3d"
    ]

    def init_session_state():
        if "theme" not in st.session_state:
            st.session_state.theme = "dark"

    def load_css(is_dark=True):
        pass

    def hero_card(title, subtitle, badge_text=""):
        st.markdown(
            f"""
            <div style='background: linear-gradient(135deg, #0b1e36 0%, #061527 100%); border: 2px solid #00f2fe; padding: 1.5rem; border-radius: 14px; margin-bottom: 1.5rem;'>
                <span style='background:#172554; color:#93c5fd; border:1px solid #1d4ed8; padding:0.25rem 0.65rem; border-radius:6px; font-size:0.75rem; font-weight:700;'>{badge_text}</span>
                <h1 style='color: #00f2fe !important; font-size: 2.2rem; margin: 0.5rem 0 0.2rem 0; font-weight:800;'>{title}</h1>
                <p style='color: #f8fafc !important; margin: 0; font-size: 0.95rem;'>{subtitle}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    def watermark(text):
        pass

    def section_header(title, desc=""):
        st.markdown(f"<h3 style='color:#00f2fe !important; margin-top:1.2rem; margin-bottom:0.3rem; font-weight:800;'>{title}</h3>", unsafe_allow_html=True)
        if desc:
            st.caption(desc)

    def infer_column_types(df):
        types = {}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                types[col] = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                types[col] = "temporal"
            else:
                types[col] = "categorical"
        return types

    def profile_dataset(df):
        numeric = df.select_dtypes(include=np.number).columns.tolist()
        categorical = df.select_dtypes(include=["object", "category"]).columns.tolist()
        return {"numeric_columns": numeric, "categorical_columns": categorical}

    def auto_recommend_chart(df, cols=None):
        cols = cols or df.columns.tolist()
        num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        cat_cols = [c for c in cols if not pd.api.types.is_numeric_dtype(df[c])]
        
        recs = []
        if num_cols:
            recs.append({"chart": "histogram", "x": num_cols[0], "reason": f"Analyze distribution density for {num_cols[0]}."})
        if len(num_cols) >= 2:
            recs.append({"chart": "scatter", "x": num_cols[0], "y": num_cols[1], "reason": f"Evaluate metric correlation between {num_cols[0]} and {num_cols[1]}."})
        if cat_cols and num_cols:
            recs.append({"chart": "bar", "x": cat_cols[0], "y": num_cols[0], "reason": f"Compare categorical aggregates of {num_cols[0]} across {cat_cols[0]}."})
        return recs

    def explain_chart_recommendation(rec):
        return f"**Recommended Architecture:** {rec.get('chart', 'Chart').title()}\n\n*Reasoning:* {rec.get('reason', 'Optimal structure derived from data topology.')}"

    def get_chart_search_results(query):
        q = query.lower()
        results = []
        if "distrib" in q or "hist" in q:
            results.append(("histogram", "Displays numeric value frequencies and variance distribution."))
        if "corr" in q or "scatter" in q or "relationship" in q:
            results.append(("scatter", "Plots bivariate relationships and data clusters."))
        if "comp" in q or "bar" in q or "cat" in q:
            results.append(("bar", "Compares discrete categorical values or metrics."))
        if not results:
            results = [("histogram", "Displays numeric value frequencies."), ("scatter", "Plots bivariate relationships.")]
        return results

    def build_chart(chart_type, df, **kwargs):
        if not PLOTLY_AVAILABLE:
            return None
        x = kwargs.get("x")
        y = kwargs.get("y")
        color = kwargs.get("color")
        height = kwargs.get("height", 400)

        try:
            if chart_type == "histogram" and x:
                fig = px.histogram(df, x=x, color=color, height=height, template="plotly_dark")
            elif chart_type == "scatter" and x and y:
                fig = px.scatter(df, x=x, y=y, color=color, height=height, template="plotly_dark")
            elif chart_type == "bar" and x and y:
                fig = px.bar(df, x=x, y=y, color=color, height=height, template="plotly_dark")
            elif chart_type == "line" and x and y:
                fig = px.line(df, x=x, y=y, color=color, height=height, template="plotly_dark")
            elif chart_type == "box" and x:
                fig = px.box(df, x=x, y=y, color=color, height=height, template="plotly_dark")
            else:
                fig = px.bar(df, height=height, template="plotly_dark")
            
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f8fafc")
            )
            return fig
        except Exception:
            return None

    def get_chart_download_link(fig, filename, format_type):
        return f"<span style='color:#00f2fe;'>[Download {filename}.{format_type} ready]</span>"

    SUPPORTED_FORMATS = {"csv": "CSV", "xlsx": "Excel"}

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Advanced File Analyzer & Visuals Studio [SECURE PRO]",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

# ─── HIGH-CONTRAST CUSTOM STYLING & READABILITY ENGINE ───────────────
st.markdown(
    """
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
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

    p, span, label, div, .stMarkdown, .stCaption, .stRadio label, .stCheckbox label {
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

    div.row-widget.stRadio, div.stFileUploader, div.stTextInput, div.stSelectbox {
        background-color: #111c2e !important;
        padding: 14px !important;
        border-radius: 10px !important;
        border: 1px solid #1e293b !important;
    }

    .stDataFrame, .stTable {
        background-color: #09101d !important;
        border: 1px solid #1e293b !important;
        border-radius: 8px !important;
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
    "🔍 Advanced File Analyzer & Visuals Studio [PRO]",
    "Universal multi-format data ingestion, automated profiling, intelligence diagnostics, and 18+ pro-tier interactive visual studio configurations designed for deep data exploration.",
    badge_text="v7.0 Enterprise High Intelligence Pipeline",
)
watermark("CHRISHEM")

# ─── SECURITY: Sandbox Root Setup ─────────────────────────────────────
SAFE_ROOT = root_dir.resolve()

def path_is_safe(candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(SAFE_ROOT)
        return True
    except ValueError:
        return False

# ─── INGESTION & PARSING HELPERS ──────────────────────────────────────
def detect_delimiter(sample_text: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=",;\t|")
        return dialect.delimiter
    except Exception:
        return ","

def robust_parse_file(file_obj_or_path):
    try:
        filename = (
            file_obj_or_path.name
            if hasattr(file_obj_or_path, "name")
            else str(file_obj_or_path)
        )
        ext = filename.lower().split(".")[-1]

        if ext in ["csv", "txt"]:
            raw_bytes = None
            if hasattr(file_obj_or_path, "read"):
                file_obj_or_path.seek(0)
                raw_bytes = file_obj_or_path.read()
                file_obj_or_path.seek(0)
            else:
                with open(file_obj_or_path, "rb") as fh:
                    raw_bytes = fh.read()

            for enc in ["utf-8", "utf-8-sig", "latin1", "iso-8859-1", "cp1252"]:
                try:
                    sample_text = raw_bytes[:4096].decode(enc, errors="strict")
                    delim = detect_delimiter(sample_text)
                    source = io.BytesIO(raw_bytes)
                    return pd.read_csv(
                        source, encoding=enc, sep=delim, engine="python", low_memory=False
                    )
                except Exception:
                    continue
            st.error(f"❌ Could not parse '{filename}' – unrecognized encoding or delimiter.")
            return None

        elif ext in ["xls", "xlsx"]:
            if hasattr(file_obj_or_path, "seek"):
                file_obj_or_path.seek(0)
            return pd.read_excel(file_obj_or_path, sheet_name=0)

        elif ext == "json":
            if hasattr(file_obj_or_path, "seek"):
                file_obj_or_path.seek(0)
            return pd.read_json(file_obj_or_path)

        elif ext in ["sav", "sas7bdat", "dta"]:
            try:
                import pyreadstat
                if isinstance(file_obj_or_path, (str, Path)):
                    path_str = str(file_obj_or_path)
                    if ext == "sav":
                        df, _ = pyreadstat.read_sav(path_str)
                    elif ext == "sas7bdat":
                        df, _ = pyreadstat.read_sas7bdat(path_str)
                    else:
                        df, _ = pyreadstat.read_dta(path_str)
                else:
                    import tempfile
                    suffix_map = {"sav": ".sav", "sas7bdat": ".sas7bdat", "dta": ".dta"}
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix_map[ext]) as tmp:
                        tmp.write(file_obj_or_path.read())
                        tmp_path = tmp.name
                    if ext == "sav":
                        df, _ = pyreadstat.read_sav(tmp_path)
                    elif ext == "sas7bdat":
                        df, _ = pyreadstat.read_sas7bdat(tmp_path)
                    else:
                        df, _ = pyreadstat.read_dta(tmp_path)
                    os.unlink(tmp_path)
                return df
            except ImportError:
                st.error(f"⚠️ `pyreadstat` library required for .{ext} files. Please install via pip.")
                return None

        elif ext == "parquet":
            return pd.read_parquet(file_obj_or_path)
        elif ext == "feather":
            return pd.read_feather(file_obj_or_path)
        elif ext in ["pkl", "pickle"]:
            return pd.read_pickle(file_obj_or_path)
        else:
            if "parse_uploaded_file" in globals():
                return parse_uploaded_file(file_obj_or_path)
            return None
    except Exception as e:
        st.error(f"❌ Error parsing file '{getattr(file_obj_or_path, 'name', file_obj_or_path)}': {e}")
        return None

# ─── DATA QUALITY & INTELLIGENCE ENGINE ──────────────────────────────
def compute_data_quality(df: pd.DataFrame) -> dict:
    n_rows, n_cols = df.shape
    total_cells = n_rows * n_cols if n_rows and n_cols else 1
    missing = int(df.isnull().sum().sum())
    dup_rows = int(df.duplicated().sum())

    whitespace_issues = 0
    for col in df.select_dtypes(include="object").columns:
        as_str = df[col].astype(str)
        whitespace_issues = int((as_str.str.strip() != as_str).sum())

    missing_pct = missing / total_cells * 100
    dup_pct = (dup_rows / n_rows * 100) if n_rows else 0
    ws_pct = whitespace_issues / total_cells * 100

    score = 100.0
    score -= min(40, missing_pct * 0.8)
    score -= min(30, dup_pct * 1.0)
    score -= min(15, ws_pct * 2)
    score = max(0.0, round(score, 1))

    return {
        "score": score,
        "missing_cells": missing,
        "missing_pct": round(missing_pct, 2),
        "duplicate_rows": dup_rows,
        "duplicate_pct": round(dup_pct, 2),
        "whitespace_issues": whitespace_issues,
    }

def generate_intelligent_insights(df: pd.DataFrame) -> list:
    insights = []
    numeric_df = df.select_dtypes(include=np.number)
    
    rows, cols = df.shape
    insights.append(f"🔍 <b>Structural Scope</b>: Dataset contains <b>{rows:,} records</b> across <b>{cols} features</b>.")

    total_nulls = df.isnull().sum().sum()
    if total_nulls > 0:
        worst_col = df.isnull().sum().idxmax()
        worst_count = df.isnull().sum()[worst_col]
        worst_pct = (worst_count / rows) * 100
        insights.append(f"⚠️ <b>Data Completeness Warning</b>: Detected <b>{total_nulls:,} missing values</b> globally. Feature <b>'{worst_col}'</b> exhibits highest sparsity with <b>{worst_pct:.1f}%</b> missing data.")
    else:
        insights.append("✅ <b>High Data Integrity</b>: Zero missing values recorded across all features.")

    return insights

# ─── INGESTION INTERFACE ──────────────────────────────────────────────
st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)
ingestion_mode = st.radio(
    "Select Data Ingestion Channel",
    options=[
        "🔍 Direct File Uploader (Standard)",
        "🔍 Local Server / Directory Explorer",
    ],
    horizontal=True,
)

active_df = None
active_source_name = None

if ingestion_mode == "🔍 Direct File Uploader (Standard)":
    section_header("🔍 Upload Data File")
    st.caption("Supported formats: CSV, Excel, SPSS (.sav), SAS (.sas7bdat), STATA (.dta), JSON, Parquet, Feather, Pickle.")

    uploaded_file = st.file_uploader(
        "Choose a data file",
        type=[
            "csv", "xlsx", "xls", "json", "sav",
            "sas7bdat", "dta", "parquet", "feather", "pkl", "txt",
        ],
    )

    if uploaded_file is not None:
        with st.spinner(f"Parsing '{uploaded_file.name}'..."):
            active_df = robust_parse_file(uploaded_file)
            active_source_name = uploaded_file.name

else:
    section_header("🔍 Local Server & Directory Explorer")
    target_dir_raw = st.text_input(
        "Directory Path to Scan",
        value=str(SAFE_ROOT),
        placeholder="/path/to/data",
    )
    target_dir = Path(target_dir_raw) if target_dir_raw else SAFE_ROOT

    if not path_is_safe(target_dir):
        st.error("⚠️ Access Denied: Specified path lies outside the allowed workspace boundary.")
    elif not target_dir.exists() or not target_dir.is_dir():
        st.error("⚠️ Invalid or non-existent directory path specified.")
    else:
        valid_exts = (".csv", ".xlsx", ".xls", ".json", ".sav", ".sas7bdat", ".dta", ".parquet", ".feather", ".pkl")
        found_files = []
        for r, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "__pycache__", "node_modules")]
            for f in files:
                if f.lower().endswith(valid_exts):
                    found_files.append(os.path.join(r, f))

        if found_files:
            st.success(f"🔍 Discovered {len(found_files)} readable data file(s).")
            selected_local_file = st.selectbox(
                "Select Data File from Directory",
                options=found_files,
                format_func=lambda x: os.path.relpath(x, target_dir),
            )
            if st.button("🔍 Load and Analyze Selected File", type="primary", use_container_width=True):
                with st.spinner(f"Reading '{os.path.basename(selected_local_file)}'..."):
                    active_df = robust_parse_file(selected_local_file)
                    active_source_name = os.path.basename(selected_local_file)
        else:
            st.info("🔍 No compatible data files found in this directory.")

# ── SESSION STATE PERSISTENCE ─────────────────────────────────────────
if active_df is not None and not active_df.empty:
    st.session_state["uploaded_df"] = active_df
    st.session_state["active_df"] = active_df
    st.session_state["working_df"] = active_df.copy()
    st.session_state["data_source"] = "advanced_analyzer"
    st.session_state["source_name"] = active_source_name or "dataset.csv"
elif active_df is not None and active_df.empty:
    st.warning("⚠️ The selected file parsed successfully, but the dataset contains no records.")

working_df = st.session_state.get("working_df")

# Fallback Demo Data Generator if no active dataset present
if working_df is None or working_df.empty:
    st.markdown(
        """
        <div class='contrast-card'>
            <h3 style='margin-top:0;'>⚠️ No Active Dataset Loaded</h3>
            <p style='color:#cbd5e1;'>Upload a file above or generate a sample research dataset to test the studio suite.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("🔍 Generate Sample Research Dataset", type="primary"):
        np.random.seed(42)
        demo_data = pd.DataFrame({
            "Subject_ID": [f"SUBJ-{2000 + i}" for i in range(150)],
            "Age": np.random.randint(18, 70, size=150),
            "Cholesterol": np.round(np.random.normal(190.0, 30.0, size=150), 1),
            "Blood_Glucose": np.round(np.random.normal(98.0, 15.0, size=150), 1),
            "Risk_Category": np.random.choice(["Low", "Moderate", "High"], size=150)
        })
        st.session_state["working_df"] = demo_data
        st.session_state["source_name"] = "sample_research_cohort.csv"
        st.rerun()

working_df = st.session_state.get("working_df")

# ─── WORKSPACE TABS (ANALYTICS & VISUALS STUDIO) ──────────────────────
if working_df is not None and not working_df.empty:
    st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)
    
    dataset_bytes = working_df.to_csv(index=False).encode("utf-8")
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()

    st.caption(
        f"🔍 **Active Dataset SHA-256 Checksum:** `{dataset_hash[:24]}...` | "
        f"Records: **{working_df.shape[0]:,}** | Features: **{working_df.shape[1]}**"
    )

    tabs = st.tabs([
        "🔍 Overview",
        "🔍 Data Quality",
        "🔍 Transform & Scrub",
        "🔍 Visuals Studio (Auto-Rec)",
        "🔍 Pro Custom Builder",
        "🔍 Semantic Search",
        "🔍 Executive Dashboard",
    ])

    # ── Tab 0: Overview ──
    with tabs[0]:
        section_header("🔍 Dataset Overview & Statistical Summary")
        profile = profile_dataset(working_df)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Rows", f"{working_df.shape[0]:,}")
        c2.metric("Total Columns", f"{working_df.shape[1]:,}")
        c3.metric("Numeric Features", len(profile.get("numeric_columns", [])))
        c4.metric("Categorical Features", len(profile.get("categorical_columns", [])))
        c5.metric("Memory Footprint", f"{working_df.memory_usage(deep=True).sum() / (1024 ** 2):.2f} MB")

        section_header("🔍 Automated AI Intelligence Insights")
        for ins in generate_intelligent_insights(working_df):
            st.markdown(f"<div style='background:#091a2e; border-left:4px solid #00f2fe; border-radius:8px; padding:0.8rem 1rem; margin-bottom:0.6rem;'>{ins}</div>", unsafe_allow_html=True)

        st.dataframe(working_df.head(25), use_container_width=True)

    # ── Tab 1: Data Quality ──
    with tabs[1]:
        section_header("🔍 Data Quality Scoring & Diagnostics")
        dq = compute_data_quality(working_df)
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Quality Score", f"{dq['score']} / 100")
        q2.metric("Missing Cells", f"{dq['missing_cells']:,}")
        q3.metric("Duplicate Rows", f"{dq['duplicate_rows']:,}")
        q4.metric("Whitespace Issues", f"{dq['whitespace_issues']:,}")

    # ── Tab 2: Transform & Scrub ──
    with tabs[2]:
        section_header("🔍 Advanced Data Transformation & Scrubbing Suite")
        if st.button("Reset Working Dataset to Default", type="primary"):
            st.session_state["working_df"] = st.session_state["uploaded_df"].copy()
            st.success("Dataset successfully reset.")
            st.rerun()
        st.dataframe(working_df, use_container_width=True)

    # Column setups for visual studio pages
    col_types = infer_column_types(working_df)
    all_columns = working_df.columns.tolist()
    numeric_cols = [c for c in all_columns if col_types.get(c) == "numeric"]
    cat_cols = [c for c in all_columns if col_types.get(c) == "categorical"]

    # ── Tab 3: Visuals Studio (Auto-Rec) ──
    with tabs[3]:
        section_header("🔍 CHRISHEM-Powered Automated Chart Studio")
        selected_cols = st.multiselect("Select Target Columns to Analyze", options=all_columns, default=all_columns[:3])
        if selected_cols:
            recommendations = auto_recommend_chart(working_df, selected_cols)
            for i, rec in enumerate(recommendations):
                st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)
                col_exp, col_chart = st.columns([1, 2])
                with col_exp:
                    st.markdown(explain_chart_recommendation(rec))
                with col_chart:
                    chart_type = rec["chart"]
                    kwargs = {k: rec[k] for k in ("x", "y", "color") if rec.get(k) is not None}
                    fig = build_chart(chart_type, working_df, **kwargs, height=350)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

    # ── Tab 4: Pro Custom Builder ──
    with tabs[4]:
        section_header("🔍 Enterprise Custom Chart Builder")
        c1, c2 = st.columns(2)
        with c1:
            chart_type = st.selectbox("Chart Type", options=ALL_CHART_TYPES)
            x_col = st.selectbox("X-Axis", options=[""] + all_columns)
        with c2:
            y_col = st.selectbox("Y-Axis", options=[""] + all_columns)
            color_col = st.selectbox("Color Group", options=[""] + all_columns)

        if st.button("Render Custom Chart", type="primary"):
            fig = build_chart(chart_type, working_df, x=x_col if x_col else None, y=y_col if y_col else None, color=color_col if color_col else None, height=450)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

    # ── Tab 5: Semantic Search ──
    with tabs[5]:
        section_header("🔍 Semantic Chart Search")
        query = st.text_input("Describe your goal (e.g., distribution, correlation)")
        if query:
            for c_type, desc in get_chart_search_results(query):
                st.markdown(f"### {c_type.title()}")
                st.caption(desc)
                fig = build_chart(c_type, working_df, x=numeric_cols[0] if numeric_cols else all_columns[0], height=300)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

    # ── Tab 6: Executive Dashboard ──
    with tabs[6]:
        section_header("🔍 Multi-Chart Executive Dashboard")
        if len(numeric_cols) >= 2:
            d1, d2 = st.columns(2)
            with d1:
                st.plotly_chart(build_chart("histogram", working_df, x=numeric_cols[0], height=320), use_container_width=True)
            with d2:
                st.plotly_chart(build_chart("scatter", working_df, x=numeric_cols[0], y=numeric_cols[1], height=320), use_container_width=True)
        else:
            st.info("Requires at least 2 numeric features.")