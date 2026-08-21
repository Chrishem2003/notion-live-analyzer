import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import hashlib
import io
import json
import re
import tempfile
import time
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# High-Performance Engines
try:
    import duckdb

    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

try:
    import polars as pl

    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False

# Visualization & ML Utilities
try:
    import plotly.express as px
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from sklearn.ensemble import IsolationForest

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from modules.page_bootstrap import render_standard_footer, setup_page
from modules.session_manager import (
    dataset_summary,
    generate_sample_dataset,
    get_active_dataframe,
    set_active_dataframe,
)
from modules.shared_ui import (
    hero_card,
    metric_card,
    render_dataset_context_banner,
    render_export_buttons,
    section_header,
)

FORBIDDEN_SQL_KEYWORDS = [
    "ATTACH",
    "DETACH",
    "COPY",
    "PRAGMA",
    "INSTALL",
    "LOAD",
    "EXPORT",
    "IMPORT",
    "CREATE",
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "CALL",
    "SET",
    "VACUUM",
    "READ_CSV",
    "READ_PARQUET",
    "READ_JSON",
    "GLOB",
    "COPY_FROM",
]
SQL_RESULT_ROW_CAP = 10000


# =============================================================================
# 🧬 CORE PIPELINE & STATE ENGINE
# =============================================================================


def robust_parse_file(file_obj_or_path):
    """Multi-format enterprise parser with Polars fast-path fallback."""
    try:
        filename = (
            file_obj_or_path.name
            if hasattr(file_obj_or_path, "name")
            else str(file_obj_or_path)
        )
        ext = filename.lower().split(".")[-1]

        # Polars Fast-Path Ingestion
        if POLARS_AVAILABLE and ext in ["csv", "parquet"]:
            try:
                if ext == "csv":
                    return pl.read_csv(file_obj_or_path).to_pandas()
                elif ext == "parquet":
                    return pl.read_parquet(file_obj_or_path).to_pandas()
            except Exception:
                pass  # Fallback to Pandas below

        if ext in ["csv", "txt"]:
            raw_bytes = (
                file_obj_or_path.read()
                if hasattr(file_obj_or_path, "read")
                else open(file_obj_or_path, "rb").read()
            )
            for enc in ["utf-8", "utf-8-sig", "latin1", "iso-8859-1", "cp1252"]:
                try:
                    return pd.read_csv(
                        io.BytesIO(raw_bytes),
                        encoding=enc,
                        engine="python",
                        low_memory=False,
                    )
                except (UnicodeDecodeError, UnicodeError):
                    continue
            return None
        elif ext in ["xls", "xlsx"]:
            return pd.read_excel(file_obj_or_path)
        elif ext == "json":
            return pd.read_json(file_obj_or_path)
        elif ext in ["sav", "sas7bdat", "dta"]:
            try:
                import pyreadstat

                path = file_obj_or_path
                if hasattr(file_obj_or_path, "read"):
                    suffix_map = {
                        "sav": ".sav",
                        "sas7bdat": ".sas7bdat",
                        "dta": ".dta",
                    }
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=suffix_map[ext]
                    ) as tmp:
                        tmp.write(file_obj_or_path.read())
                        path = tmp.name
                reader = {
                    "sav": pyreadstat.read_sav,
                    "sas7bdat": pyreadstat.read_sas7bdat,
                    "dta": pyreadstat.read_dta,
                }[ext]
                df, _ = reader(path)
                return df
            except ImportError:
                st.error("⚠️ `pyreadstat` required for SPSS/SAS/STATA files.")
                return None
        elif ext == "parquet":
            return pd.read_parquet(file_obj_or_path)
        elif ext in ["pkl", "pickle"]:
            return pd.read_pickle(file_obj_or_path)
        return None
    except Exception as e:
        st.error(f"❌ Enterprise Parse Error: {e}}")
        return None


def dataset_fingerprint(df: pd.DataFrame) -> str:
    """SHA-256 fingerprint of dataset schema and content."""
    hasher = hashlib.sha256()
    hasher.update(",".join(df.columns.astype(str)).encode("utf-8"))
    hasher.update(pd.util.hash_pandas_object(df, index=False).values.tobytes())
    return hasher.hexdigest()


def schema_signature(df: pd.DataFrame) -> dict:
    return {col: str(dtype) for col, dtype in df.dtypes.items()}


def initialize_recipe_engine():
    if "transform_recipe" not in st.session_state:
        st.session_state["transform_recipe"] = []
    if "dataset_history" not in st.session_state:
        st.session_state["dataset_history"] = []
    if "dataset_schema_meta" not in st.session_state:
        st.session_state["dataset_schema_meta"] = {}


def push_to_history(df: pd.DataFrame, action: str):
    """State Versioning & Undo Buffer."""
    initialize_recipe_engine()
    if len(st.session_state["dataset_history"]) > 10:
        st.session_state["dataset_history"].pop(0)  # Maintain top 10 states
    st.session_state["dataset_history"].append(
        {"df": df.copy(), "timestamp": datetime.now(), "action": action}
    )


def log_transformation(step_type: str, description: str, params: dict):
    initialize_recipe_engine()
    st.session_state["transform_recipe"].append(
        {
            "step": step_type,
            "description": description,
            "params": params,
            "timestamp": pd.Timestamp.now().isoformat(),
        }
    )


def apply_recipe_step(df: pd.DataFrame, step: dict) -> pd.DataFrame:
    kind = step["step"]
    p = step["params"]

    if kind == "Clean Dataset":
        out = df.copy()
        if p.get("strip_ws"):
            for c in out.select_dtypes(include=["object"]).columns:
                out[c] = out[c].astype(str).str.strip()
        if p.get("drop_dups"):
            out = out.drop_duplicates()
        strat = p.get("impute_strategy", "None")
        if strat == "Drop rows with missing values":
            out = out.dropna()
        elif strat == "Mean Imputation (Numeric)":
            num_cols = out.select_dtypes(include=[np.number]).columns
            out[num_cols] = out[num_cols].fillna(out[num_cols].mean())
        elif strat == "Median Imputation (Numeric)":
            num_cols = out.select_dtypes(include=[np.number]).columns
            out[num_cols] = out[num_cols].fillna(out[num_cols].median())
        elif strat == "Mode Imputation (Categorical/All)":
            out = out.fillna(out.mode().iloc[0])
        elif strat == "Forward/Backward Fill":
            out = out.ffill().bfill()
        return out

    if kind == "Encode Feature":
        out = df.copy()
        col, method = p["column"], p["method"]
        if method == "One-Hot Encoding":
            out = pd.get_dummies(
                out, columns=[col], prefix=col, drop_first=p.get("drop_first", False)
            )
        elif method == "Label / Categorical Encoding":
            out[f"{col}}_encoded"] = out[col].astype("category").cat.codes
        return out

    if kind == "Transform Feature":
        out = df.copy()
        col, method = p["column"], p["method"]
        if method == "Log Transformation (log1p)":
            out[f"{col}}_log"] = np.log1p(np.maximum(0, out[col]))
        elif method == "Square Root":
            out[f"{col}}_sqrt"] = np.sqrt(np.maximum(0, out[col]))
        elif method == "Polynomial (Degree 2)":
            out[f"{col}}_sq"] = np.power(out[col], 2)
        return out

    if kind == "Compute Feature":
        out = df.copy()
        col1, col2, op, new_col = (
            p["col1"],
            p["col2"],
            p["operation"],
            p["new_col"],
        )
        if "+" in op:
            out[new_col] = out[col1] + out[col2]
        elif "-" in op:
            out[new_col] = out[col1] - out[col2]
        elif "*" in op:
            out[new_col] = out[col1] * out[col2]
        elif "/" in op:
            out[new_col] = np.where(
                out[col2] == 0, np.nan, out[col1] / out[col2]
            )
        return out

    if kind == "Enforce Schema":
        out = df.copy()
        for col, target in p.get("types", {}).items():
            if col not in out.columns:
                continue
            if target == "Numeric":
                out[col] = pd.to_numeric(out[col], errors="coerce")
            elif target == "Category":
                out[col] = out[col].astype("category")
            elif target == "Date":
                out[col] = pd.to_datetime(out[col], errors="coerce")
            elif target == "String":
                out[col] = out[col].astype(str)
        return out

    return df


# =============================================================================
# 🖥️ MODULE TABS
# =============================================================================


def render_ingestion_tab():
    section_header(
        "📥 Enterprise Data Ingestion Hub",
        "High-performance multi-engine parser with schema tracking and version rollback.",
    )
    col_up, col_sample = st.columns([1.4, 1])

    with col_up:
        st.markdown("#### 📄 Ingestion Pipeline")
        uploaded_file = st.file_uploader(
            "Upload structured dataset (CSV, Excel, JSON, Parquet, SAS, SPSS)",
            type=[
                "csv",
                "xlsx",
                "xls",
                "json",
                "sav",
                "sas7bdat",
                "dta",
                "parquet",
                "pkl",
            ],
            key="enterprise_data_uploader",
        )
        if uploaded_file is not None:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.info(
                f"📦 File detected: `{uploaded_file.name}}` ({file_size_mb:.2f}} MB)"
            )

            with st.spinner("Processing & validating dataset..."):
                df = robust_parse_file(uploaded_file)
                if df is not None and not df.empty:
                    new_fp = dataset_fingerprint(df)
                    set_active_dataframe(df, uploaded_file.name)
                    push_to_history(df, f"Ingested {uploaded_file.name}}")
                    st.session_state["dataset_schema_meta"] = {
                        "fingerprint": new_fp,
                        "schema": schema_signature(df),
                    }
                    st.success(
                        f"✅ Successfully ingested `{uploaded_file.name}}` —"
                        f" {df.shape[0]:,}} rows × {df.shape[1]}} columns"
                    )
                    st.dataframe(df.head(10), use_container_width=True)

    with col_sample:
        st.markdown("#### 🎲 Preset Industry Cohorts")
        sample_kinds = {
            "Clinical Trial Cohort": "clinical",
            "Customer Analytics": "marketing",
            "Financial Transactions": "sales",
            "Genomic Microarray": "genomic",
        }
        for label, kind in sample_kinds.items():
            if st.button(label, use_container_width=True, key=f"smp_{kind}}"):
                sample_df = generate_sample_dataset(kind)
                set_active_dataframe(sample_df, f"{kind}}_sample.csv")
                push_to_history(sample_df, f"Loaded preset: {label}}")
                st.session_state["dataset_schema_meta"] = {
                    "fingerprint": dataset_fingerprint(sample_df),
                    "schema": schema_signature(sample_df),
                }
                st.success(f"✅ Loaded {label}}")
                st.rerun()


def render_quality_tab():
    df = get_active_dataframe()
    section_header(
        "🔍 Data Health & Advanced Anomaly Scan",
        "Deep null-state profiling, Isolation Forest anomaly isolation, and cleaning.",
    )

    if df is None:
        st.warning("No active dataset loaded.")
        return

    # Metrics Summary
    total_cells = df.shape[0] * df.shape[1]
    missing = int(df.isnull().sum().sum())
    dups = int(df.duplicated().sum())
    completeness = (
        ((total_cells - missing) / total_cells * 100) if total_cells else 100
    )
    health_score = max(
        0.0,
        100.0
        - (missing / max(total_cells, 1) * 50)
        - (dups / max(df.shape[0], 1) * 50),
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Completeness", f"{completeness:.2f}}%")
    c2.metric("Missing Values", f"{missing:,}}")
    c3.metric("Duplicate Rows", f"{dups:,}}")
    c4.metric("Dataset Health Index", f"{health_score:.1f}}%")

    tab1, tab2, tab3 = st.tabs(
        [
            "📊 Schema & Missingness",
            "🤖 Isolation Forest Anomaly Scan",
            "🛠️ Auto-Remediation",
        ]
    )

    with tab1:
        schema_df = pd.DataFrame(
            {
                "Column": df.columns,
                "Inferred Type": df.dtypes.astype(str),
                "Missing Values": df.isnull().sum().values,
                "Missing %": (df.isnull().mean() * 100).round(2).values,
                "Unique Values": df.nunique().values,
            }
        )
        st.dataframe(schema_df, use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("#### Unsupervised Outlier Isolation (ML Driven)")
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(num_cols) < 2 or not SKLEARN_AVAILABLE:
            st.info(
                "Requires Scikit-Learn and at least 2 numeric columns for"
                " multivariate anomaly detection."
            )
        else:
            contamination = st.slider(
                "Estimated Outlier Ratio (Contamination)",
                0.01,
                0.20,
                0.05,
                0.01,
            )
            if st.button("🚀 Run Isolation Forest Scan", type="primary"):
                clf = IsolationForest(
                    contamination=contamination, random_state=42
                )
                sub_df = df[num_cols].dropna()
                preds = clf.fit_predict(sub_df)
                anomalies = sub_df[preds == -1]
                st.warning(
                    f"⚠️ Isolated {len(anomalies):,}} potential anomalous rows"
                    f" ({len(anomalies)/len(sub_df)*100:.2f}}% of total)."
                )
                st.dataframe(
                    df.loc[anomalies.index], use_container_width=True
                )

    with tab3:
        st.markdown("#### Applied Remediation Sandbox")
        strip_ws = st.checkbox(
            "Strip whitespace from string columns", value=True
        )
        drop_dups = st.checkbox("Remove exact duplicates", value=False)
        impute_strat = st.selectbox(
            "Imputation Strategy",
            [
                "None",
                "Drop rows with missing values",
                "Mean Imputation (Numeric)",
                "Median Imputation (Numeric)",
                "Mode Imputation (Categorical/All)",
                "Forward/Backward Fill",
            ],
        )

        if st.button("🧹 Apply Remediation Protocol", type="primary"):
            params = {
                "strip_ws": strip_ws,
                "drop_dups": drop_dups,
                "impute_strategy": impute_strat,
            }
            push_to_history(df, "Dataset Remediation")
            cleaned = apply_recipe_step(
                df, {"step": "Clean Dataset", "params": params}
            )
            set_active_dataframe(
                cleaned, st.session_state.get("source_name", "remediated.csv")
            )
            log_transformation(
                "Clean Dataset", f"Impute: {impute_strat}}", params
            )
            st.success("✅ Dataset successfully remediated.")
            st.rerun()


def render_transform_tab():
    df = get_active_dataframe()
    section_header(
        "⚙️ Feature Engineering & Transformation",
        "Encode, scale, compute features, and review history.",
    )

    if df is None:
        st.warning("No active dataset loaded.")
        return

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🧮 Compute Engine",
            "🏷️ Encoding & Recode",
            "📈 Mathematical Transforms",
            "📜 Recipe History & Undo",
        ]
    )

    with tab1:
        if len(num_cols) >= 2:
            c1, c2, c3, c4 = st.columns(4)
            var_a = c1.selectbox("Variable A", num_cols, key="comp_a")
            op = c2.selectbox(
                "Operation",
                ["Add (+)", "Subtract (-)", "Multiply (*)", "Divide (/)"],
            )
            var_b = c3.selectbox("Variable B", num_cols, key="comp_b")
            new_col = c4.text_input("New Column Name", value="computed_feature")

            if st.button("⚡ Compute", type="primary"):
                push_to_history(df, f"Computed feature {new_col}}")
                params = {
                    "col1": var_a,
                    "col2": var_b,
                    "operation": op,
                    "new_col": new_col,
                }
                updated = apply_recipe_step(
                    df, {"step": "Compute Feature", "params": params}
                )
                set_active_dataframe(updated, "transformed.csv")
                log_transformation(
                    "Compute Feature", f"{new_col}} = {var_a}} {op}} {var_b}}", params
                )
                st.success(f"✅ Generated `{new_col}}`.")
                st.rerun()

    with tab2:
        if cat_cols:
            enc_col = st.selectbox("Category Variable", cat_cols)
            enc_method = st.selectbox(
                "Encoder Strategy",
                ["One-Hot Encoding", "Label / Categorical Encoding"],
            )
            if st.button("🚀 Apply Encoder", type="primary"):
                push_to_history(df, f"Encoded {enc_col}}")
                params = {"column": enc_col, "method": enc_method}
                updated = apply_recipe_step(
                    df, {"step": "Encode Feature", "params": params}
                )
                set_active_dataframe(updated, "encoded.csv")
                log_transformation("Encode Feature", f"{enc_method}} on {enc_col}}", params)
                st.success("✅ Feature encoded successfully.")
                st.rerun()

    with tab3:
        if num_cols:
            trans_col = st.selectbox("Target Numeric Feature", num_cols)
            trans_method = st.selectbox(
                "Transformation",
                [
                    "Log Transformation (log1p)",
                    "Square Root",
                    "Polynomial (Degree 2)",
                ],
            )
            if st.button("📈 Apply Math Transform", type="primary"):
                push_to_history(df, f"Transformed {trans_col}}")
                params = {"column": trans_col, "method": trans_method}
                updated = apply_recipe_step(
                    df, {"step": "Transform Feature", "params": params}
                )
                set_active_dataframe(updated, "transformed.csv")
                log_transformation(
                    "Transform Feature",
                    f"{trans_method}} on {trans_col}}",
                    params,
                )
                st.success("✅ Transformation complete.")
                st.rerun()

    with tab4:
        st.markdown("#### Version Control & Replay Pipeline")
        history = st.session_state.get("dataset_history", [])
        if history and st.button("⏪ Undo Last Action"):
            if len(history) > 1:
                st.session_state["dataset_history"].pop()
                prev_state = st.session_state["dataset_history"][-1]["df"]
                set_active_dataframe(prev_state, "rolled_back.csv")
                st.success("✅ Rolled back to prior dataset snapshot.")
                st.rerun()
            else:
                st.info("At initial dataset state.")

        st.json(st.session_state.get("transform_recipe", []))


def render_analytics_viz_tab():
    df = get_active_dataframe()
    section_header(
        "📊 Dynamic Analytics & Visualization Engine",
        "Interactive Plotly exploration for trends, distributions, and correlations.",
    )

    if df is None:
        st.warning("No active dataset loaded.")
        return

    if not PLOTLY_AVAILABLE:
        st.error("Plotly is required for interactive visualizations.")
        return

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    all_cols = df.columns.tolist()

    v_tab1, v_tab2, v_tab3 = st.tabs(
        [
            "📈 Dynamic Chart Builder",
            "🔥 Correlation Heatmap",
            "📊 Multivariate Matrix",
        ]
    )

    with v_tab1:
        c1, c2, c3, c4 = st.columns(4)
        chart_type = c1.selectbox(
            "Chart Type", ["Scatter", "Line", "Bar", "Histogram", "Box Plot"]
        )
        x_col = c2.selectbox("X-Axis", all_cols)
        y_col = c3.selectbox(
            "Y-Axis",
            [None] + num_cols,
            index=1 if len(num_cols) > 0 else 0,
        )
        color_col = c4.selectbox("Color Segment", [None] + all_cols)

        if chart_type == "Scatter" and y_col:
            fig = px.scatter(df, x=x_col, y=y_col, color=color_col)
        elif chart_type == "Line" and y_col:
            fig = px.line(df, x=x_col, y=y_col, color=color_col)
        elif chart_type == "Bar":
            fig = px.bar(df, x=x_col, y=y_col, color=color_col)
        elif chart_type == "Histogram":
            fig = px.histogram(df, x=x_col, color=color_col)
        elif chart_type == "Box Plot" and y_col:
            fig = px.box(df, x=x_col, y=y_col, color=color_col)

        if "fig" in locals():
            st.plotly_chart(fig, use_container_width=True)

    with v_tab2:
        if len(num_cols) > 1:
            corr = df[num_cols].corr()
            fig_corr = px.imshow(
                corr,
                text_auto=True,
                aspect="auto",
                color_continuous_scale="Blues",
            )
            st.plotly_chart(fig_corr, use_container_width=True)

    with v_tab3:
        if len(num_cols) >= 2:
            selected_vars = st.multiselect(
                "Select Features for Matrix",
                num_cols,
                default=num_cols[: min(4, len(num_cols))],
            )
            if len(selected_vars) >= 2:
                fig_matrix = px.scatter_matrix(df, dimensions=selected_vars)
                st.plotly_chart(fig_matrix, use_container_width=True)


def render_explorer_sql_tab():
    df = get_active_dataframe()
    section_header(
        "📋 Data Explorer & DuckDB SQL Console",
        "Query high-volume data using high-speed, sandboxed DuckDB SQL queries.",
    )

    if df is None:
        st.warning("No active dataset loaded.")
        return

    tab_view, tab_sql, tab_export = st.tabs(
        ["👁️ Data Inspector", "⚡ DuckDB Console", "📥 Export Hub"]
    )

    with tab_view:
        st.dataframe(df, use_container_width=True)

    with tab_sql:
        if DUCKDB_AVAILABLE:
            st.caption("Read-only SQL environment. Query table via `df`.")
            default_query = f"SELECT * FROM df LIMIT 50"
            sql_query = st.text_area(
                "SQL Statement", value=default_query, height=100
            )

            if st.button("🚀 Execute SQL Query", type="primary"):
                # Keyword validation check
                upper_q = sql_query.upper()
                forbidden = [
                    kw
                    for kw in FORBIDDEN_SQL_KEYWORDS
                    if re.search(rf"\b{kw}}\b", upper_q)
                ]
                if forbidden:
                    st.error(
                        f"🚫 Query contains forbidden keywords: {forbidden}}"
                    )
                else:
                    try:
                        conn = duckdb.connect(database=":memory:")
                        conn.register("df", df)
                        res = conn.execute(sql_query).df()
                        conn.close()
                        st.success(f"✅ Executed — returned {len(res):,}} rows.")
                        st.dataframe(res, use_container_width=True)
                        render_export_buttons(res, base_name="query_results")
                    except Exception as e:
                        st.error(f"SQL Execution Error: {e}}")
        else:
            st.info("DuckDB engine not available in environment.")

    with tab_export:
        render_export_buttons(df, base_name="processed_dataset")


# =============================================================================
# 🚀 MAIN CONTROLLER
# =============================================================================


def main():
    from modules.subscription import require_active_subscription
    from modules.user_preferences import (
        render_accent_color_css,
        render_readability_fix,
    )

    require_active_subscription(hub_id="data")
    setup_page("Enterprise Data Studio", "📄", initial_sidebar_state="expanded")

    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "📄 Enterprise Data Studio (Ultra)",
        "Next-generation data workbench featuring Polars acceleration, DuckDB SQL execution, automated feature engineering, and state undo/redo capabilities.",
        badge_text="ENTERPRISE STUDIO • ULTRA TIER",
    )

    render_dataset_context_banner()

    tabs = st.tabs(
        [
            "📥 Ingestion Hub",
            "🔍 Quality & Anomalies",
            "⚙️ Transform Studio",
            "📊 Interactive Visuals",
            "📋 Explorer & SQL",
        ]
    )

    with tabs[0]:
        render_ingestion_tab()
    with tabs[1]:
        render_quality_tab()
    with tabs[2]:
        render_transform_tab()
    with tabs[3]:
        render_analytics_viz_tab()
    with tabs[4]:
        render_explorer_sql_tab()

    render_standard_footer("ENTERPRISE DATA STUDIO")


if __name__ == "__main__":
    main()
