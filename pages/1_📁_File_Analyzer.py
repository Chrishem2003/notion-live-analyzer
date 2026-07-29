# ═══════════════════════════════════════════════════════════════════════════════
# ADVANCED FILE ANALYZER & MULTI-FORMAT INGESTION ENGINE [ENTERPRISE EDITION]
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

# Optional charting backend — degrade gracefully if not installed
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

# Fallback robust imports for core modules
try:
  from modules.config import init_session_state
  from modules.data_processor import infer_column_types, profile_dataset
  from modules.export import render_export_buttons
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
except ImportError:
  def init_session_state():
    if "theme" not in st.session_state:
      st.session_state.theme = "dark"

  def load_css(is_dark=True):
    pass

  def hero_card(title, subtitle, badge_text=""):
    st.title(title)
    st.markdown(f"*{subtitle}* — `[{badge_text}]`")

  def watermark(text):
    pass

  def section_header(title, desc=""):
    st.subheader(title)
    if desc:
      st.caption(desc)

  SUPPORTED_FORMATS = {"csv": "CSV", "xlsx": "Excel"}


# ─── Page Configuration ───────────────────────────────────────────────
st.set_page_config(
    page_title="Advanced File Analyzer [SECURE]",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

# ─── Custom Deep Dark Styling ─────────────────────────────────────────
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0d1117 !important;
        color: #f0f6fc !important;
    }
    h1, h2, h3, h4, h5, h6, span, p, label, .stMarkdown, .stCaption {
        color: #f0f6fc !important;
    }
    .stDataFrame, .stTable {
        background-color: #161b22 !important;
    }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_card(
    "📁 Advanced File Analyzer & Explorer Engine",
    "Universal data parsing for CSV, Excel, SPSS (.sav), SAS, STATA, JSON, and binary formats "
    "with automated profiling, data-quality scoring, anomaly detection, and visualization.",
    badge_text="v6.0 Enterprise — Cryptographic Integrity & Pipeline Automation",
)
watermark("CHRISHEM")

# ─── SECURITY: Sandbox Root Setup ─────────────────────────────────────
SAFE_ROOT = root_dir.resolve()


def path_is_safe(candidate: Path) -> bool:
  """Ensure file browsing stays contained within the allowed local workspace."""
  try:
    candidate.resolve().relative_to(SAFE_ROOT)
    return True
  except ValueError:
    return False


# ─── Ingestion & Parsing Helpers ──────────────────────────────────────
def detect_delimiter(sample_text: str) -> str:
  try:
    dialect = csv.Sniffer().sniff(sample_text, delimiters=",;\t|")
    return dialect.delimiter
  except Exception:
    return ","


def robust_parse_file(file_obj_or_path):
  """Robust multi-format research document parser."""
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
      st.error(
          f"❌ Could not parse '{filename}' — unrecognized encoding or"
          " delimiter."
      )
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
          with tempfile.NamedTemporaryFile(
              delete=False, suffix=suffix_map[ext]
          ) as tmp:
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
        st.error(
            f"⚠️ `pyreadstat` library required for .{ext} files. Please install"
            " via pip."
        )
        return None

    elif ext == "parquet":
      return pd.read_parquet(file_obj_or_path)
    elif ext == "feather":
      return pd.read_feather(file_obj_or_path)
    elif ext in ["pkl", "pickle"]:
      return pd.read_pickle(file_obj_or_path)
    else:
      return (
          parse_uploaded_file(file_obj_or_path)
          if "parse_uploaded_file" in globals()
          else None
      )
  except Exception as e:
    st.error(
        f"❌ Error parsing file '{getattr(file_obj_or_path, 'name', file_obj_or_path)}':"
        f" {e}"
    )
    return None


# ─── Data Quality & Analytics Utilities ───────────────────────────────
def compute_data_quality(df: pd.DataFrame) -> dict:
  n_rows, n_cols = df.shape
  total_cells = n_rows * n_cols if n_rows and n_cols else 1
  missing = int(df.isnull().sum().sum())
  dup_rows = int(df.duplicated().sum())

  whitespace_issues = 0
  for col in df.select_dtypes(include="object").columns:
    as_str = df[col].astype(str)
    whitespace_issues += int((as_str.str.strip() != as_str).sum())

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


def detect_outliers_iqr(series: pd.Series) -> pd.Series:
  clean = series.dropna()
  if clean.empty:
    return pd.Series(dtype=series.dtype)
  q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
  iqr = q3 - q1
  lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
  return clean[(clean < lower) | (clean > upper)]


def detect_outliers_zscore(series: pd.Series, threshold: float = 3.0) -> pd.Series:
  clean = series.dropna()
  if clean.empty or clean.std() == 0:
    return pd.Series(dtype=series.dtype)
  z = (clean - clean.mean()) / clean.std()
  return clean[z.abs() > threshold]


EMAIL_RE = re.compile(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+")
PHONE_RE = re.compile(r"(\+?\d[\d\-\s()]{7,}\d)")


def mask_pii(df: pd.DataFrame, columns: list) -> pd.DataFrame:
  masked = df.copy()
  for col in columns:
    masked[col] = (
        masked[col]
        .astype(str)
        .apply(
            lambda v: PHONE_RE.sub(
                "[PHONE MASKED]", EMAIL_RE.sub("[EMAIL MASKED]", v)
            )
        )
    )
  return masked


def generate_pandas_snippet(source_name: str, ops: list) -> str:
  lines = [
      f'import pandas as pd',
      f'df = pd.read_csv("{source_name}")  # adjust loader to match source format',
      '',
  ]
  lines.extend(ops)
  return "\n".join(lines)


# ─── Main Interface Setup ─────────────────────────────────────────────
st.markdown("---")
ingestion_mode = st.radio(
    "Select Data Ingestion Channel",
    options=[
        "📤 Direct File Uploader (Standard)",
        "📂 Local Server / Directory Explorer",
    ],
    horizontal=True,
)

active_df = None
active_source_name = None

if ingestion_mode == "📤 Direct File Uploader (Standard)":
  section_header("📤 Upload Data File")
  st.caption(
      "Supported formats: CSV, Excel, SPSS (.sav), SAS (.sas7bdat), STATA"
      " (.dta), JSON, Parquet, Feather, Pickle."
  )

  uploaded_file = st.file_uploader(
      "Choose a data file",
      type=[
          "csv",
          "xlsx",
          "xls",
          "json",
          "sav",
          "sas7bdat",
          "dta",
          "parquet",
          "feather",
          "pkl",
          "txt",
      ],
      help="Upload dataset for instant profiling, quality checks, and visualization.",
  )

  if uploaded_file is not None:
    with st.spinner(f"Parsing '{uploaded_file.name}'..."):
      active_df = robust_parse_file(uploaded_file)
      active_source_name = uploaded_file.name

else:
  section_header("📂 Local Server & Directory Explorer")
  st.info(
      "🔒 Sandboxed securely to the workspace directory. External paths are"
      " restricted."
  )

  target_dir_raw = st.text_input(
      "Directory Path to Scan",
      value=str(SAFE_ROOT),
      placeholder="/path/to/data",
  )
  target_dir = Path(target_dir_raw) if target_dir_raw else SAFE_ROOT

  if not path_is_safe(target_dir):
    st.error(
        "⚠️ Access Denied: Specified path lies outside the allowed workspace"
        " boundary."
    )
  elif not target_dir.exists() or not target_dir.is_dir():
    st.error("⚠️ Invalid or non-existent directory path specified.")
  else:
    valid_exts = (
        ".csv",
        ".xlsx",
        ".xls",
        ".json",
        ".sav",
        ".sas7bdat",
        ".dta",
        ".parquet",
        ".feather",
        ".pkl",
    )
    found_files = []
    for r, dirs, files in os.walk(target_dir):
      dirs[:] = [
          d
          for d in dirs
          if not d.startswith(".")
          and d not in ("venv", "__pycache__", "node_modules")
      ]
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
      if st.button(
          "🚀 Load and Analyze Selected File",
          type="primary",
          use_container_width=True,
      ):
        with st.spinner(
            f"Reading '{os.path.basename(selected_local_file)}'..."
        ):
          active_df = robust_parse_file(selected_local_file)
          active_source_name = os.path.basename(selected_local_file)
    else:
      st.info("📭 No compatible data files found in this directory.")

# ── Session Management & State Persistence ───────────────────────────
if active_df is not None and not active_df.empty:
  st.session_state["uploaded_df"] = active_df
  st.session_state["active_df"] = active_df
  st.session_state["working_df"] = active_df.copy()
  st.session_state["data_source"] = "advanced_analyzer"
  st.session_state["source_name"] = active_source_name or "dataset.csv"
  st.session_state.setdefault("transform_log", [])
  st.session_state["transform_log"] = []
elif active_df is not None and active_df.empty:
  st.warning(
      "⚠️ The selected file parsed successfully, but the dataset contains no"
      " records."
  )

working_df = st.session_state.get("working_df")

# ─── Advanced Feature Workspace Tabs ───────────────────────────────────
if working_df is not None and not working_df.empty:
  st.markdown("---")

  # Cryptographic Ledger Hash generation for dataset versioning
  dataset_bytes = working_df.to_csv(index=False).encode("utf-8")
  dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()

  st.caption(
      f"🔗 **Active Dataset SHA-256 Checksum:** `{dataset_hash[:24]}...` |"
      f" Records: **{working_df.shape[0]:,}** | Features:"
      f" **{working_df.shape[1]}**"
  )

  tabs = st.tabs([
      "📊 Overview",
      "🩺 Data Quality",
      "👁️ Preview & Filter",
      "🛠️ Transform",
      "📈 Visualize",
      "🧮 Aggregate",
      "📥 Export & Code",
      "🔗 Merge",
  ])

  # ── Tab 0: Overview ──
  with tabs[0]:
    section_header("📊 Dataset Overview & Statistical Summary")
    profile = (
        profile_dataset(working_df)
        if "profile_dataset" in globals()
        else {"numeric_columns": [], "categorical_columns": []}
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Rows", f"{working_df.shape[0]:,}")
    c2.metric("Total Columns", f"{working_df.shape[1]:,}")
    c3.metric(
        "Numeric Features",
        len(
            profile.get(
                "numeric_columns",
                working_df.select_dtypes(include=np.number).columns,
            )
        ),
    )
    c4.metric(
        "Categorical Features",
        len(
            profile.get(
                "categorical_columns",
                working_df.select_dtypes(
                    include=["object", "category"]
                ).columns,
            )
        ),
    )
    mem_mb = working_df.memory_usage(deep=True).sum() / (1024 ** 2)
    c5.metric("Memory Footprint", f"{mem_mb:.2f} MB")

    section_header("📋 Column Metadata & Data Types")
    col_types = (
        infer_column_types(working_df)
        if "infer_column_types" in globals()
        else {c: str(working_df[c].dtype) for c in working_df.columns}
    )
    type_df = pd.DataFrame([
        {
            "Column Name": col,
            "Pandas Type": str(working_df[col].dtype),
            "Inferred Type": ctype,
            "Null Count": int(working_df[col].isnull().sum()),
            "Null %": round(working_df[col].isnull().mean() * 100, 2),
            "Unique Values": int(working_df[col].nunique()),
        }
        for col, ctype in col_types.items()
    ])
    st.dataframe(type_df, use_container_width=True, hide_index=True)

  # ── Tab 1: Data Quality ──
  with tabs[1]:
    section_header("🩺 Comprehensive Data Quality & Health Assessment")
    dq = compute_data_quality(working_df)

    score_color = (
        "🟢" if dq["score"] >= 80 else "🟡" if dq["score"] >= 50 else "🔴"
    )
    q1, q2, q3, q4 = st.columns(4)
    q1.metric(f"{score_color} Health Score", f"{dq['score']}/100")
    q2.metric(
        "Missing Cells", f"{dq['missing_cells']:,}", f"{dq['missing_pct']}%"
    )
    q3.metric(
        "Duplicate Rows",
        f"{dq['duplicate_rows']:,}",
        f"{dq['duplicate_pct']}%",
    )
    q4.metric("Whitespace Issues", f"{dq['whitespace_issues']:,}")

    st.markdown("##### Missing Values Breakdown")
    na_counts = working_df.isnull().sum()
    na_df = (
        na_counts[na_counts > 0].sort_values(ascending=False).reset_index()
    )
    na_df.columns = ["Column", "Missing Count"]
    if not na_df.empty:
      na_df["Missing %"] = round(
          na_df["Missing Count"] / len(working_df) * 100, 2
      )
      st.dataframe(na_df, use_container_width=True, hide_index=True)
      if PLOTLY_AVAILABLE:
        fig_na = px.bar(
            na_df,
            x="Column",
            y="Missing Count",
            title="Missing Values Distribution per Column",
            color="Missing Count",
            color_continuous_scale="Reds",
        )
        st.plotly_chart(fig_na, use_container_width=True)
    else:
      st.success("✅ Perfect data integrity: Zero missing values detected.")

    st.markdown("##### Statistical Outlier Detection (Numeric Fields)")
    numeric_cols = working_df.select_dtypes(include=np.number).columns.tolist()
    if numeric_cols:
      outlier_col = st.selectbox(
          "Select Target Feature", numeric_cols, key="outlier_col"
      )
      method = st.radio(
          "Detection Algorithm",
          ["IQR Method (1.5×)", "Z-Score Threshold (>3.0)"],
          horizontal=True,
          key="outlier_method",
      )
      series = working_df[outlier_col]
      outliers = (
          detect_outliers_iqr(series)
          if method.startswith("IQR")
          else detect_outliers_zscore(series)
      )
      st.write(
          f"Identified **{len(outliers)}** outlier record(s) in `{outlier_col}`"
          f" ({len(outliers)/len(series)*100:.2f}% of valid entries)."
      )
      if len(outliers) > 0:
        st.dataframe(outliers.to_frame(name=outlier_col), use_container_width=True)
    else:
      st.info("No numeric features available for outlier analysis.")

  # ── Tab 2: Preview & Filter ──
  with tabs[2]:
    section_header("👁️ Interactive Data Preview & Filtering Sandbox")
    filtered_df = working_df

    with st.expander("🔎 Advanced Multi-Condition Filtering", expanded=False):
      filter_col = st.selectbox(
          "Filter by Column", ["(none)"] + list(working_df.columns), key="filter_col"
      )
      if filter_col != "(none)":
        col_series = working_df[filter_col]
        if pd.api.types.is_numeric_dtype(col_series):
          lo, hi = float(col_series.min()), float(col_series.max())
          if lo < hi:
            rng = st.slider(
                "Numerical Range", lo, hi, (lo, hi), key="filter_range"
            )
            filtered_df = filtered_df[
                (filtered_df[filter_col] >= rng[0])
                & (filtered_df[filter_col] <= rng[1])
            ]
        else:
          options = col_series.dropna().unique().tolist()
          chosen = st.multiselect(
              "Allowed Categories",
              options,
              default=options[: min(10, len(options))],
              key="filter_values",
          )
          if chosen:
            filtered_df = filtered_df[filtered_df[filter_col].isin(chosen)]

    search_term = st.text_input(
        "🔍 Global Text Search across all columns", key="global_search"
    )
    if search_term:
      mask = (
          filtered_df.astype(str)
          .apply(
              lambda row: row.str.contains(search_term, case=False, na=False)
          )
          .any(axis=1)
      )
      filtered_df = filtered_df[mask]

    sc1, sc2 = st.columns([2, 1])
    with sc1:
      sort_by = st.selectbox(
          "Sort records by column", ["(none)"] + list(working_df.columns), key="sort_col"
      )
    with sc2:
      sort_dir = st.radio(
          "Sort Direction", ["Ascending", "Descending"], horizontal=True, key="sort_dir"
      )
    if sort_by != "(none)":
      filtered_df = filtered_df.sort_values(
          by=sort_by, ascending=(sort_dir == "Ascending")
      )

    row_limit = st.slider(
        "Display Row Limit",
        min_value=10,
        max_value=max(10, min(1000, len(filtered_df))),
        value=min(50, max(10, len(filtered_df))),
        step=10,
    )
    st.caption(
        f"Displaying {min(row_limit, len(filtered_df))} of"
        f" **{len(filtered_df):,}** filtered rows (total working dataset:"
        f" {len(working_df):,})."
    )
    st.dataframe(
        filtered_df.head(row_limit), use_container_width=True, hide_index=True
    )

    if st.checkbox(
        "Show Comprehensive Descriptive Statistics (`.describe()`)",
        value=True,
        key="show_describe",
    ):
      with st.expander("📈 Statistical Distribution Breakdown"):
        st.dataframe(filtered_df.describe(include="all"), use_container_width=True)

  # ── Tab 3: Transform ──
  with tabs[3]:
    section_header("🛠️ Schema & Data Transformation Suite")
    st.caption(
        "All modifications instantly update the active working session and log"
        " reproducible Python code."
    )

    t1, t2, t3 = st.columns(3)

    with t1:
      st.markdown("**Rename Feature**")
      rn_col = st.selectbox("Column to Rename", working_df.columns, key="rn_col")
      rn_new = st.text_input("New Column Name", key="rn_new")
      if st.button("Apply Rename", key="btn_rename") and rn_new:
        st.session_state["working_df"] = working_df.rename(
            columns={rn_col: rn_new}
        )
        st.session_state["transform_log"].append(
            f'df = df.rename(columns={{ "{rn_col}": "{rn_new}" }})'
        )
        st.success(f"Renamed `{rn_col}` to `{rn_new}`.")
        st.rerun()

    with t2:
      st.markdown("**Drop Features**")
      drop_cols = st.multiselect(
          "Select Columns to Remove", working_df.columns, key="drop_cols"
      )
      if st.button("Apply Drop", key="btn_drop") and drop_cols:
        st.session_state["working_df"] = working_df.drop(columns=drop_cols)
        st.session_state["transform_log"].append(
            f"df = df.drop(columns={drop_cols})"
        )
        st.success(f"Removed columns: {', '.join(drop_cols)}")
        st.rerun()

    with t3:
      st.markdown("**Type Conversion**")
      cv_col = st.selectbox(
          "Target Column", working_df.columns, key="cv_col_trans"
      )
      cv_type = st.selectbox(
          "Target Type",
          ["string", "float", "int", "datetime", "category"],
          key="cv_type",
      )
      if st.button("Apply Type Conversion", key="btn_convert"):
        try:
          new_df = working_df.copy()
          if cv_type == "datetime":
            new_df[cv_col] = pd.to_datetime(new_df[cv_col], errors="coerce")
          elif cv_type == "int":
            new_df[cv_col] = (
                pd.to_numeric(new_df[cv_col], errors="coerce").astype("Int64")
            )
          elif cv_type == "float":
            new_df[cv_col] = pd.to_numeric(new_df[cv_col], errors="coerce")
          else:
            new_df[cv_col] = new_df[cv_col].astype(cv_type)
          st.session_state["working_df"] = new_df
          st.session_state["transform_log"].append(
              f'df["{cv_col}"] = df["{cv_col}"].astype("{cv_type}")'
          )
          st.success(f"Converted `{cv_col}` to `{cv_type}` successfully.")
          st.rerun()
        except Exception as e:
          st.error(f"Type conversion failed: {e}")

    st.markdown("---")
    m1, m2 = st.columns(2)
    with m1:
      st.markdown("**Missing Value Imputation & Cleanse**")
      mv_col = st.selectbox(
          "Target Field", ["(all columns)"] + list(working_df.columns), key="mv_col"
      )
      mv_action = st.radio(
          "Imputation Strategy",
          [
              "Drop rows with nulls",
              "Fill with mean",
              "Fill with median",
              "Fill with mode",
              "Fill with 0 / empty string",
          ],
          key="mv_action",
      )
      if st.button("Execute Imputation", key="btn_mv"):
        new_df = working_df.copy()
        cols_target = (
            list(new_df.columns) if mv_col == "(all columns)" else [mv_col]
        )
        if mv_action == "Drop rows with nulls":
          new_df = new_df.dropna(subset=cols_target)
        else:
          for c in cols_target:
            if mv_action == "Fill with mean" and pd.api.types.is_numeric_dtype(
                new_df[c]
            ):
              new_df[c] = new_df[c].fillna(new_df[c].mean())
            elif (
                mv_action == "Fill with median"
                and pd.api.types.is_numeric_dtype(new_df[c])
            ):
              new_df[c] = new_df[c].fillna(new_df[c].median())
            elif mv_action == "Fill with mode":
              mode_val = new_df[c].mode()
              if not mode_val.empty:
                new_df[c] = new_df[c].fillna(mode_val[0])
            elif mv_action == "Fill with 0 / empty string":
              fill_val = 0 if pd.api.types.is_numeric_dtype(new_df[c]) else ""
              new_df[c] = new_df[c].fillna(fill_val)
        st.session_state["working_df"] = new_df
        st.session_state["transform_log"].append(
            f"# Imputation applied: {mv_action} on {cols_target}"
        )
        st.success("Missing value processing complete.")
        st.rerun()

    with m2:
      st.markdown("**PII Anonymization Sandbox**")
      pii_cols = st.multiselect(
          "Select columns containing PII (Emails / Phone Numbers)",
          working_df.select_dtypes(include="object").columns.tolist(),
          key="pii_cols",
      )
      if st.button("Apply PII Masking", key="btn_pii") and pii_cols:
        st.session_state["working_df"] = mask_pii(working_df, pii_cols)
        st.session_state["transform_log"].append(
            f"# PII masking applied to: {pii_cols}"
        )
        st.success(
            f"Successfully scrubbed PII patterns in: {', '.join(pii_cols)}"
        )
        st.rerun()

    st.markdown("---")
    if st.button("↩️ Reset Working Dataset to Original Source", key="btn_reset"):
      st.session_state["working_df"] = st.session_state["active_df"].copy()
      st.session_state["transform_log"] = []
      st.success("Dataset restored to initial ingestion state.")
      st.rerun()

  # ── Tab 4: Visualize ──
  with tabs[4]:
    section_header("📈 Advanced Interactive Visual Analytics")
    if not PLOTLY_AVAILABLE:
      st.warning(
          "⚠️ Plotly package not detected. Install via `pip install plotly` for"
          " interactive charts."
      )
    else:
      numeric_cols = working_df.select_dtypes(include=np.number).columns.tolist()
      categorical_cols = working_df.select_dtypes(
          include=["object", "category"]
      ).columns.tolist()
      datetime_cols = working_df.select_dtypes(
          include="datetime"
      ).columns.tolist()

      chart_type = st.selectbox(
          "Select Visualization Type",
          [
              "Histogram",
              "Scatter Plot",
              "Bar Chart (Category Counts)",
              "Time Series Line Plot",
              "Correlation Heatmap",
          ],
      )

      if chart_type == "Histogram" and numeric_cols:
        col = st.selectbox("Select Numeric Column", numeric_cols, key="hist_col")
        fig = px.histogram(
            working_df,
            x=col,
            title=f"Distribution Profile: {col}",
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

      elif chart_type == "Scatter Plot" and len(numeric_cols) >= 2:
        cx, cy = st.columns(2)
        x_col = cx.selectbox("X-Axis Feature", numeric_cols, key="sx")
        y_col = cy.selectbox(
            "Y-Axis Feature",
            numeric_cols,
            index=min(1, len(numeric_cols) - 1),
            key="sy",
        )
        color_col = st.selectbox(
            "Color Grouping (Optional)", ["(none)"] + categorical_cols, key="scolor"
        )
        fig = px.scatter(
            working_df,
            x=x_col,
            y=y_col,
            color=None if color_col == "(none)" else color_col,
            title=f"Bivariate Scatter: {y_col} vs {x_col}",
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

      elif chart_type == "Bar Chart (Category Counts)" and categorical_cols:
        col = st.selectbox(
            "Select Categorical Feature", categorical_cols, key="bar_col"
        )
        counts = (
            working_df[col].value_counts().head(30).reset_index()
        )
        counts.columns = [col, "Frequency"]
        fig = px.bar(
            counts,
            x=col,
            y="Frequency",
            title=f"Top Category Counts: {col}",
            template="plotly_dark",
            color="Frequency",
            color_continuous_scale="Viridis",
        )
        st.plotly_chart(fig, use_container_width=True)

      elif chart_type == "Time Series Line Plot" and datetime_cols and numeric_cols:
        dt_col = st.selectbox("Date / Timestamp Column", datetime_cols, key="ts_dt")
        val_col = st.selectbox("Metric Value Column", numeric_cols, key="ts_val")
        ts_df = working_df[[dt_col, val_col]].dropna().sort_values(dt_col)
        fig = px.line(
            ts_df,
            x=dt_col,
            y=val_col,
            title=f"Temporal Trend: {val_col} over {dt_col}",
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

      elif chart_type == "Correlation Heatmap" and len(numeric_cols) >= 2:
        corr = working_df[numeric_cols].corr(numeric_only=True)
        fig = px.imshow(
            corr,
            text_auto=".2f",
            aspect="auto",
            title="Pearson Correlation Matrix",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

      else:
        st.info(
            "⚠️ Insufficient matching columns in dataset for this visualization"
            " mode."
        )

  # ── Tab 5: Aggregate ──
  with tabs[5]:
    section_header("🧮 Group-By & Multi-Metric Aggregation")
    categorical_cols = working_df.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()
    numeric_cols = working_df.select_dtypes(include=np.number).columns.tolist()

    if categorical_cols and numeric_cols:
      group_cols = st.multiselect(
          "Group By Attributes", categorical_cols, key="agg_group"
      )
      agg_col = st.selectbox(
          "Target Numeric Feature", numeric_cols, key="agg_col"
      )
      agg_funcs = st.multiselect(
          "Aggregation Functions",
          ["sum", "mean", "median", "count", "std", "min", "max"],
          default=["sum", "mean", "count"],
          key="agg_funcs",
      )
      if group_cols and agg_funcs:
        result = (
            working_df.groupby(group_cols)[agg_col]
            .agg(agg_funcs)
            .reset_index()
        )
        st.dataframe(result, use_container_width=True, hide_index=True)
        if PLOTLY_AVAILABLE and len(group_cols) == 1 and agg_funcs:
          fig_agg = px.bar(
              result,
              x=group_cols[0],
              y=agg_funcs[0],
              title=f"{agg_funcs[0].title()} of {agg_col} grouped by {group_cols[0]}",
              template="plotly_dark",
          )
          st.plotly_chart(fig_agg, use_container_width=True)
      else:
        st.info("Please select at least one grouping attribute and function.")
    else:
      st.info(
          "Aggregation requires both categorical and numeric features in the"
          " dataset."
      )

  # ── Tab 6: Export & Code ──
  with tabs[6]:
    section_header("📥 Export Processed Dataset & Pipeline Code")
    
    e1, e2 = st.columns(2)
    with e1:
      st.markdown("##### Export Working Dataset")
      export_format = st.selectbox(
          "Export Format", ["CSV", "Excel", "JSON", "Parquet"], key="export_fmt"
      )
      
      if export_format == "CSV":
        mime_type = "text/csv"
        file_data = working_df.to_csv(index=False).encode("utf-8")
        file_name = "processed_dataset.csv"
      elif export_format == "Excel":
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
          working_df.to_excel(writer, index=False, sheet_name="Sheet1")
        file_data = buffer.getvalue()
        file_name = "processed_dataset.xlsx"
      elif export_format == "JSON":
        mime_type = "application/json"
        file_data = working_df.to_json(orient="records", indent=2).encode("utf-8")
        file_name = "processed_dataset.json"
      else: # Parquet
        mime_type = "application/octet-stream"
        buffer = io.BytesIO()
        working_df.to_parquet(buffer, index=False)
        file_data = buffer.getvalue()
        file_name = "processed_dataset.parquet"

      st.download_button(
          label=f"⬇️ Download as {export_format}",
          data=file_data,
          file_name=file_name,
          mime=mime_type,
          use_container_width=True,
      )

    with e2:
      st.markdown("##### Reproducible Pandas Pipeline Code")
      transform_ops = st.session_state.get("transform_log", [])
      code_snippet = generate_pandas_snippet(
          active_source_name or "dataset.csv", transform_ops
      )
      st.code(code_snippet, language="python")

  # ── Tab 7: Merge ──
  with tabs[7]:
    section_header("🔗 Multi-Dataset Join & Merge Sandbox")
    st.caption("Merge your current working dataset with a secondary uploaded file or directory source.")

    secondary_file = st.file_uploader(
        "Upload Secondary Dataset to Merge",
        type=["csv", "xlsx", "xls", "json", "parquet"],
        key="secondary_uploader",
    )

    if secondary_file is not None:
      secondary_df = robust_parse_file(secondary_file)
      if secondary_df is not None and not secondary_df.empty:
        st.success(f"Successfully parsed secondary dataset: '{secondary_file.name}' ({secondary_df.shape[0]:,} rows, {secondary_df.shape[1]} columns).")

        mc1, mc2, mc3 = st.columns(3)
        with mc1:
          left_on = st.selectbox("Primary Dataset Key Column", working_df.columns, key="merge_left_on")
        with mc2:
          right_on = st.selectbox("Secondary Dataset Key Column", secondary_df.columns, key="merge_right_on")
        with mc3:
          how_join = st.selectbox("Join Type", ["inner", "left", "right", "outer"], key="merge_how")

        if st.button("🚀 Execute Dataset Merge", type="primary", use_container_width=True):
          try:
            merged_df = pd.merge(
                working_df,
                secondary_df,
                left_on=left_on,
                right_on=right_on,
                how=how_join,
                suffixes=("_primary", "_secondary"),
            )
            st.session_state["working_df"] = merged_df
            st.session_state["transform_log"].append(
                f'df = pd.merge(df, secondary_df, left_on="{left_on}", right_on="{right_on}", how="{how_join}")'
            )
            st.success(f"Merge successful! New dataset shape: {merged_df.shape[0]:,} rows × {merged_df.shape[1]} columns.")
            st.rerun()
          except Exception as e:
            st.error(f"❌ Merge operation failed: {e}")
      else:
        st.warning("⚠️ The secondary dataset is empty or could not be parsed.")
    else:
      st.info("ℹ️ Upload a secondary dataset to begin joining and merging features.")