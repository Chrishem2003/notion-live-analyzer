"""
📁 Data Studio — Enterprise Data Management & Intelligence Hub (Premium)
Out-of-core-aware ingestion, a sandboxed DuckDB query engine, safe transformations, a *replayable*
JSON recipe pipeline, dataset fingerprinting, and schema drift detection.
"""

import hashlib
import io
import json
import re
import tempfile

import numpy as np
import pandas as pd
import streamlit as st

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import (
    get_active_dataframe,
    set_active_dataframe,
    generate_sample_dataset,
    dataset_summary,
)
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
    render_export_buttons,
    metric_card,
)

# DuckDB keywords disallowed in the sandboxed SQL console — anything that touches the
# filesystem, extensions, or mutates state rather than just reading the in-memory `df`.
FORBIDDEN_SQL_KEYWORDS = [
    "ATTACH", "DETACH", "COPY", "PRAGMA", "INSTALL", "LOAD", "EXPORT", "IMPORT",
    "CREATE", "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CALL", "SET",
    "VACUUM", "READ_CSV", "READ_PARQUET", "READ_JSON", "GLOB", "COPY_FROM",
]
SQL_RESULT_ROW_CAP = 5000


# ═══════════════════════════════════════════════════════════════════════
# ENTERPRISE FILE INGESTION ENGINE
# ═══════════════════════════════════════════════════════════════════════
def robust_parse_file(file_obj_or_path):
    """Enterprise multi-format parser with fallback encoding detection."""
    try:
        filename = file_obj_or_path.name if hasattr(file_obj_or_path, "name") else str(file_obj_or_path)
        ext = filename.lower().split(".")[-1]

        if ext in ["csv", "txt"]:
            raw_bytes = file_obj_or_path.read() if hasattr(file_obj_or_path, "read") else open(file_obj_or_path, "rb").read()
            for enc in ["utf-8", "utf-8-sig", "latin1", "iso-8859-1", "cp1252"]:
                try:
                    return pd.read_csv(io.BytesIO(raw_bytes), encoding=enc, engine="python", low_memory=False)
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
                    suffix_map = {"sav": ".sav", "sas7bdat": ".sas7bdat", "dta": ".dta"}
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix_map[ext]) as tmp:
                        tmp.write(file_obj_or_path.read())
                        path = tmp.name
                reader = {"sav": pyreadstat.read_sav, "sas7bdat": pyreadstat.read_sas7bdat, "dta": pyreadstat.read_dta}[ext]
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
        st.error(f"❌ Enterprise Parse Error: {e}")
        return None


def dataset_fingerprint(df: pd.DataFrame) -> str:
    """SHA-256 fingerprint of the dataset's schema + content, for version tracking and drift checks."""
    hasher = hashlib.sha256()
    hasher.update(",".join(df.columns.astype(str)).encode("utf-8"))
    hasher.update(pd.util.hash_pandas_object(df, index=False).values.tobytes())
    return hasher.hexdigest()


def schema_signature(df: pd.DataFrame) -> dict:
    return {col: str(dtype) for col, dtype in df.dtypes.items()}


def diff_schema(old_sig: dict, new_sig: dict) -> dict:
    added = sorted(set(new_sig) - set(old_sig))
    removed = sorted(set(old_sig) - set(new_sig))
    retyped = sorted(c for c in (set(old_sig) & set(new_sig)) if old_sig[c] != new_sig[c])
    return {"added": added, "removed": removed, "retyped": retyped}


# ═══════════════════════════════════════════════════════════════════════
# REPRODUCIBLE, REPLAYABLE RECIPE ENGINE
# ═══════════════════════════════════════════════════════════════════════
def initialize_recipe_engine():
    if "transform_recipe" not in st.session_state:
        st.session_state["transform_recipe"] = []
    if "dataset_schema_meta" not in st.session_state:
        st.session_state["dataset_schema_meta"] = {}


def log_transformation(step_type: str, description: str, params: dict):
    """Appends a structured, machine-replayable step."""
    initialize_recipe_engine()
    st.session_state["transform_recipe"].append({
        "step": step_type,
        "description": description,
        "params": params,
        "timestamp": pd.Timestamp.now().isoformat(),
    })


def apply_recipe_step(df: pd.DataFrame, step: dict) -> pd.DataFrame:
    """Deterministically re-applies a single logged step to a dataframe."""
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
        elif strat == "Forward/Backward Fill":
            out = out.ffill().bfill()
        return out

    if kind == "Compute Feature":
        out = df.copy()
        col1, col2, op, new_col = p["col1"], p["col2"], p["operation"], p["new_col"]
        if col1 not in out.columns or col2 not in out.columns:
            raise KeyError(f"Replay requires columns '{col1}' and '{col2}', not present in the new dataset.")
        if "+" in op:
            out[new_col] = out[col1] + out[col2]
        elif "-" in op:
            out[new_col] = out[col1] - out[col2]
        elif "*" in op:
            out[new_col] = out[col1] * out[col2]
        elif "/" in op:
            out[new_col] = np.where(out[col2] == 0, np.nan, out[col1] / out[col2])
        else:
            out[new_col] = out[col1] / (out[col2].abs() + 1e-5)
        return out

    if kind == "Quantile Binning":
        out = df.copy()
        col, n_bins, bin_name = p["column"], p["bins"], p["bin_name"]
        if col not in out.columns:
            raise KeyError(f"Replay requires column '{col}', not present in the new dataset.")
        out[bin_name] = pd.qcut(out[col], q=n_bins, labels=[f"Tier_{i+1}" for i in range(n_bins)], duplicates="drop")
        return out

    if kind == "Scale Feature":
        out = df.copy()
        col, method = p["column"], p["method"]
        if col not in out.columns:
            raise KeyError(f"Replay requires column '{col}', not present in the new dataset.")
        if method == "Z-Score Standardization":
            std_val = out[col].std()
            if std_val and not pd.isna(std_val):
                out[f"{col}_z"] = (out[col] - out[col].mean()) / std_val
        elif method == "Min-Max Normalization":
            min_v, max_v = out[col].min(), out[col].max()
            if min_v != max_v:
                out[f"{col}_mm"] = (out[col] - min_v) / (max_v - min_v)
        else:
            out[f"{col}_pct"] = out[col].rank(pct=True)
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

    raise ValueError(f"Unknown recipe step type: {kind}")


def apply_recipe(df: pd.DataFrame, recipe: list) -> pd.DataFrame:
    out = df
    for step in recipe:
        out = apply_recipe_step(out, step)
    return out


# ═══════════════════════════════════════════════════════════════════════
# TABS & UI RENDERERS
# ═══════════════════════════════════════════════════════════════════════
def render_ingestion_tab():
    section_header("📥 Enterprise Data Ingestion Hub", "Secure ingestion pipeline supporting multi-format files, out-of-core handling, and sample generators.")

    col_up, col_sample = st.columns([1.4, 1])

    with col_up:
        st.markdown("#### 📁 File Ingestion Pipeline")
        uploaded_file = st.file_uploader(
            "Upload structured datasets (CSV, Excel, JSON, SPSS, SAS, STATA, Parquet)",
            type=["csv", "xlsx", "xls", "json", "sav", "sas7bdat", "dta", "parquet", "pkl", "txt"],
            key="enterprise_data_uploader",
        )
        if uploaded_file is not None:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.info(f"📦 File detected: `{uploaded_file.name}` ({file_size_mb:.2f} MB)")

            with st.spinner(f"Parsing and running structural validation on '{uploaded_file.name}'..."):
                df = robust_parse_file(uploaded_file)
                if df is not None and not df.empty:
                    new_fp = dataset_fingerprint(df)
                    prev_fp = st.session_state.get("dataset_schema_meta", {}).get("fingerprint")
                    prev_sig = st.session_state.get("dataset_schema_meta", {}).get("schema", {})

                    if prev_fp == new_fp:
                        st.warning("⚠️ This file is byte-for-byte identical to the currently active dataset. Ingesting anyway.")
                    elif prev_sig:
                        drift = diff_schema(prev_sig, schema_signature(df))
                        if drift["added"] or drift["removed"] or drift["retyped"]:
                            with st.expander("🔀 Schema Drift Detected vs. Previously Active Dataset", expanded=True):
                                if drift["added"]:
                                    st.write("**New columns:**", ", ".join(drift["added"]))
                                if drift["removed"]:
                                    st.write("**Missing columns:**", ", ".join(drift["removed"]))
                                if drift["retyped"]:
                                    st.write("**Type changes:**", ", ".join(drift["retyped"]))

                    set_active_dataframe(df, uploaded_file.name)
                    initialize_recipe_engine()
                    st.session_state["transform_recipe"] = []
                    st.session_state["dataset_schema_meta"] = {"fingerprint": new_fp, "schema": schema_signature(df)}

                    st.success(f"✅ Successfully ingested `{uploaded_file.name}` — {df.shape[0]:,} rows × {df.shape[1]} columns")
                    st.caption(f"🔐 Dataset fingerprint (SHA-256): `{new_fp[:24]}…`")
                    st.dataframe(df.head(10), use_container_width=True)

    with col_sample:
        st.markdown("#### 🎲 Curated Sample Data Gallery")
        st.caption("Instantly provision standardized test beds for analysis workflows.")
        sample_kinds = {
            "Clinical Cohort (150 patients)": "clinical",
            "Marketing / Customer (200)": "marketing",
            "Sales Transactions (300)": "sales",
            "Genomic Expression (100)": "genomic",
            "Survey Responses (250)": "survey",
            "Research Cohort (250)": "research",
        }
        for label, kind in sample_kinds.items():
            if st.button(label, use_container_width=True, key=f"smp_ent_{kind}"):
                sample_df = generate_sample_dataset(kind)
                set_active_dataframe(sample_df, f"{kind}_sample.csv")
                initialize_recipe_engine()
                st.session_state["transform_recipe"] = []
                st.session_state["dataset_schema_meta"] = {
                    "fingerprint": dataset_fingerprint(sample_df),
                    "schema": schema_signature(sample_df),
                }
                st.success(f"✅ Loaded {label}")
                st.rerun()


def render_quality_tab():
    df = get_active_dataframe()
    section_header("🔍 Enterprise Quality Audit & Remediation", "Deep anomaly scanning, missingness analysis, and safe data cleaning pipelines.")

    if df is None:
        st.warning("No active dataset loaded. Please ingest a dataset first.")
        return

    total_cells = df.shape[0] * df.shape[1]
    missing = int(df.isnull().sum().sum())
    dups = int(df.duplicated().sum())
    completeness = ((total_cells - missing) / total_cells * 100) if total_cells else 100
    health_score = max(0.0, 100.0 - (missing / max(total_cells, 1) * 50) - (dups / max(df.shape[0], 1) * 50))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Completeness Rate", f"{completeness:.2f}%")
    c2.metric("Missing Cells", f"{missing:,}")
    c3.metric("Duplicate Rows", f"{dups:,}")
    c4.metric("Health Score", f"{health_score:.1f}%")

    tab_audit, tab_outlier, tab_clean = st.tabs(["📊 Schema & Missingness", "⚠️ Advanced Outlier Engine", "🛠️ Automated Cleaning Pipeline"])

    with tab_audit:
        st.markdown("#### Structural Schema Audit")
        schema_df = pd.DataFrame({
            "Column": df.columns,
            "Inferred Type": df.dtypes.astype(str),
            "Null Count": df.isnull().sum().values,
            "Null Percentage (%)": (df.isnull().mean() * 100).round(2).values,
            "Distinct Count": df.nunique().values,
        })
        st.dataframe(schema_df, use_container_width=True, hide_index=True)

        report_lines = [
            "# DATA QUALITY AUDIT REPORT",
            f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Fingerprint: {st.session_state.get('dataset_schema_meta', {}).get('fingerprint', 'n/a')}",
            "",
            f"- Rows: {df.shape[0]:,} | Columns: {df.shape[1]}",
            f"- Completeness: {completeness:.2f}%",
            f"- Missing cells: {missing:,}",
            f"- Duplicate rows: {dups:,}",
            f"- Health score: {health_score:.1f}%",
            "",
            "## Per-Column Breakdown",
            schema_df.to_string(index=False),
        ]
        st.download_button("⬇️ Download Quality Audit Report (.md)", data="\n".join(report_lines), file_name="data_quality_audit.md", mime="text/markdown", key="dl_quality_report")

    with tab_outlier:
        st.markdown("#### Statistical Outlier Detection")
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            st.info("No numeric columns available for outlier identification.")
        else:
            scan_mode = st.radio("Scope", ["Single Column (Deep Dive)", "All Numeric Columns (Batch Summary)"], horizontal=True, key="ent_outlier_scope")
            method = st.radio("Detection Protocol", ["Interquartile Range (IQR 1.5x)", "Robust Z-Score (|z| > 3.0)"], horizontal=True, key="ent_outlier_method")

            def _outlier_mask(series: pd.Series) -> pd.Series:
                s = series.dropna()
                if "IQR" in method:
                    q1, q3 = np.percentile(s, 25), np.percentile(s, 75)
                    iqr = q3 - q1
                    mask = (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)
                else:
                    median = s.median()
                    mad = np.median(np.abs(s - median))
                    z = 0.6745 * (s - median) / mad if mad > 0 else pd.Series(np.zeros_like(s), index=s.index)
                    mask = np.abs(z) > 3.0
                return mask

            if scan_mode == "Single Column (Deep Dive)":
                col = st.selectbox("Select target variable", numeric_cols, key="ent_outlier_col")
                if st.button("🔍 Execute Outlier Scan", type="primary", key="ent_run_outlier"):
                    series = df[col].dropna()
                    mask = _outlier_mask(series)
                    outliers = df.loc[series[mask].index]
                    st.metric("Outlier Records Isolated", f"{len(outliers):,}")
                    if len(outliers):
                        st.dataframe(outliers, use_container_width=True)
                        render_export_buttons(outliers, base_name=f"outliers_{col}")
            else:
                if st.button("🔍 Execute Batch Outlier Scan", type="primary", key="ent_run_outlier_batch"):
                    summary = []
                    for c in numeric_cols:
                        series = df[c].dropna()
                        if series.empty:
                            continue
                        mask = _outlier_mask(series)
                        summary.append({"Column": c, "Outlier Count": int(mask.sum()), "Outlier Rate (%)": round(100 * mask.sum() / len(series), 2)})
                    summary_df = pd.DataFrame(summary).sort_values("Outlier Count", ascending=False)
                    st.dataframe(summary_df, use_container_width=True, hide_index=True)
                    render_export_buttons(summary_df, base_name="batch_outlier_summary")

    with tab_clean:
        st.markdown("#### Sandboxed Cleaning & Imputation Pipeline")
        strip_ws = st.checkbox("Strip leading/trailing whitespace from string columns", value=True, key="ent_clean_ws")
        drop_dups = st.checkbox("Remove exact duplicate rows", value=False, key="ent_clean_dups")
        impute_strat = st.selectbox("Missing Value Strategy", ["None", "Drop rows with missing values", "Mean Imputation (Numeric)", "Median Imputation (Numeric)", "Forward/Backward Fill"], key="ent_clean_impute")

        if st.button("🧹 Execute Cleaning Pipeline", type="primary", key="ent_run_clean"):
            params = {"strip_ws": strip_ws, "drop_dups": drop_dups, "impute_strategy": impute_strat}
            cleaned = apply_recipe_step(df, {"step": "Clean Dataset", "params": params})

            set_active_dataframe(cleaned, st.session_state.get("source_name", "cleaned_dataset.csv"))
            log_transformation("Clean Dataset", f"strip_ws={strip_ws}, drop_dups={drop_dups}, impute={impute_strat}", params)
            st.success("✅ Cleaning pipeline executed securely. Active state updated.")
            st.dataframe(cleaned.head(10), use_container_width=True)


def render_transform_tab():
    df = get_active_dataframe()
    section_header("⚙️ Enterprise Transform Studio", "Execute sandboxed calculations, quartile binning, scaling protocols, and replayable recipe logging.")

    if df is None:
        st.warning("No active dataset loaded. Please ingest a dataset first.")
        return

    working = df.copy()
    initialize_recipe_engine()
    num_columns = working.select_dtypes(include=[np.number]).columns.tolist()

    tab_compute, tab_bin, tab_scale, tab_recipe = st.tabs(["🧮 Safe Compute", "📊 Binning & Recode", "📈 Feature Scaling", "📜 Recipe & Replay"])

    with tab_compute:
        st.markdown("#### Safe Expression Builder")
        new_col = st.text_input("New column designation", value="engineered_ratio", key="ent_comp_col")

        if not num_columns:
            st.info("No numeric columns available.")
        else:
            col1 = st.selectbox("Numerator / Variable A", num_columns, key="ent_comp_a")
            op = st.selectbox("Operation", ["Addition (+)", "Subtraction (-)", "Multiplication (*)", "Division (/)", "Custom Safe Ratio"], key="ent_comp_op")
            col2 = st.selectbox("Denominator / Variable B", num_columns, key="ent_comp_b")

            if st.button("⚡ Compute Feature", type="primary", key="ent_run_compute"):
                try:
                    params = {"new_col": new_col, "col1": col1, "operation": op, "col2": col2}
                    working = apply_recipe_step(working, {"step": "Compute Feature", "params": params})
                    set_active_dataframe(working, st.session_state.get("source_name", "transformed.csv"))
                    log_transformation("Compute Feature", f"{new_col} = {col1} {op} {col2}", params)
                    st.success(f"✅ Successfully computed feature column `{new_col}`.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Computation failure: {e}")

    with tab_bin:
        st.markdown("#### Quantile & Equal-Interval Binning")
        if not num_columns:
            st.info("No numeric columns available.")
        else:
            col = st.selectbox("Select variable to bin", num_columns, key="ent_bin_col")
            n_bins = st.slider("Bin partitions", 2, 10, 4, key="ent_bin_count")
            bin_name = st.text_input("Output bin column name", value=f"{col}_tier", key="ent_bin_name")

            if st.button("📊 Generate Quantile Bins", type="primary", key="ent_run_bin"):
                try:
                    params = {"column": col, "bins": n_bins, "bin_name": bin_name}
                    working = apply_recipe_step(working, {"step": "Quantile Binning", "params": params})
                    set_active_dataframe(working, st.session_state.get("source_name", "binned.csv"))
                    log_transformation("Quantile Binning", f"{bin_name} = qcut({col}, {n_bins})", params)
                    st.success(f"✅ Created binned variable `{bin_name}`.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Binning error: {e}")

    with tab_scale:
        st.markdown("#### Robust Statistical Scaling")
        if not num_columns:
            st.info("No numeric columns available.")
        else:
            col = st.selectbox("Select column to scale", num_columns, key="ent_scale_col")
            method = st.selectbox("Scaling Algorithm", ["Z-Score Standardization", "Min-Max Normalization", "Percentile Rank"], key="ent_scale_method")

            if st.button("📈 Apply Scaling", type="primary", key="ent_run_scale"):
                try:
                    params = {"column": col, "method": method}
                    working = apply_recipe_step(working, {"step": "Scale Feature", "params": params})
                    set_active_dataframe(working, st.session_state.get("source_name", "scaled.csv"))
                    log_transformation("Scale Feature", f"{method} on {col}", params)
                    st.success(f"✅ Applied {method} to `{col}`.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Scaling error: {e}")

    with tab_recipe:
        st.markdown("#### Reproducible Pipeline Recipe")
        recipe = st.session_state.get("transform_recipe", [])
        if not recipe:
            st.info("No transformation steps recorded yet in the current session.")
        else:
            st.json(recipe)
            recipe_json = json.dumps(recipe, indent=2)
            st.download_button("📥 Download Pipeline Recipe (.json)", data=recipe_json, file_name="data_studio_recipe.json", mime="application/json", use_container_width=True, key="dl_recipe_json")

            st.markdown("---")
            st.markdown("#### 🔁 Replay This Recipe on a New File")
            replay_file = st.file_uploader("Upload a file to replay the recipe onto", key="ent_replay_upload")
            if replay_file is not None and st.button("▶️ Run Replay", type="primary", key="ent_run_replay"):
                fresh_df = robust_parse_file(replay_file)
                if fresh_df is None or fresh_df.empty:
                    st.error("Could not parse the uploaded file.")
                else:
                    try:
                        replayed = apply_recipe(fresh_df, recipe)
                        st.success(f"✅ Replay succeeded — {replayed.shape[0]:,} rows × {replayed.shape[1]} columns.")
                        st.dataframe(replayed.head(10), use_container_width=True)
                        render_export_buttons(replayed, base_name="recipe_replayed_dataset")
                    except (KeyError, ValueError) as e:
                        st.error(f"🚨 Replay failed at a step that doesn't match this file's schema: {e}")

            if st.button("🗑️ Clear Recipe Log", key="ent_clear_recipe"):
                st.session_state["transform_recipe"] = []
                st.rerun()


def render_variable_editor_tab():
    df = get_active_dataframe()
    section_header("🏷️ Enterprise Schema & Metadata Manager", "Manage variable types, persistence labels, and measurement scales securely.")

    if df is None:
        st.warning("No active dataset loaded. Please ingest a dataset first.")
        return

    meta_records = []
    for col in df.columns:
        is_num = pd.api.types.is_numeric_dtype(df[col])
        meta_records.append({
            "Variable": col,
            "Type": "Numeric" if is_num else "String",
            "Measurement Scale": "Scale" if is_num and df[col].nunique() > 10 else "Nominal",
            "Null Count": int(df[col].isnull().sum()),
            "Unique Count": int(df[col].nunique()),
        })
    meta_df = pd.DataFrame(meta_records)

    edited = st.data_editor(
        meta_df,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Type": st.column_config.SelectboxColumn("Type", options=["Numeric", "String", "Category", "Date"]),
            "Measurement Scale": st.column_config.SelectboxColumn("Measurement Scale", options=["Scale", "Nominal", "Ordinal"]),
        },
        hide_index=True,
        key="ent_var_editor",
    )

    if st.button("🚀 Enforce Enterprise Schema Types", type="primary", key="ent_apply_var"):
        try:
            type_map = {row["Variable"]: row["Type"] for _, row in edited.iterrows()}
            typed_df = apply_recipe_step(df, {"step": "Enforce Schema", "params": {"types": type_map}})
            set_active_dataframe(typed_df, st.session_state.get("source_name", "typed_dataset.csv"))
            log_transformation("Enforce Schema", "Type casting enforced via metadata manager", {"types": type_map})
            st.success("✅ Enterprise schema successfully applied across all workspace hubs.")
            st.dataframe(typed_df.dtypes.astype(str).reset_index().rename(columns={"index": "Column", 0: "Enforced Type"}), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Schema enforcement error: {e}")


def render_simulator_tab():
    section_header("🎲 Enterprise Synthetic Data Simulator", "Generate statistically controlled synthetic datasets for advanced staging and stress-testing.")

    n_rows = st.slider("Simulation Row Count", 100, 10000, 500, key="ent_sim_rows")
    template = st.selectbox("Simulation Template", [
        "Clinical Trial Cohort", "Customer Segmentation Analytics", "Financial Time Series", "Multivariate Gaussian Matrix"
    ], key="ent_sim_template")

    if st.button("🎲 Generate Synthetic Enterprise Dataset", type="primary", key="ent_run_sim"):
        rng = np.random.default_rng(42)
        if template == "Clinical Trial Cohort":
            df = pd.DataFrame({
                "Subject_ID": [f"SUBJ-{i:05d}" for i in range(n_rows)],
                "Age": rng.integers(20, 80, n_rows),
                "BMI": np.round(rng.normal(27.0, 4.5, n_rows), 1),
                "Systolic_BP": rng.integers(100, 175, n_rows),
                "Cholesterol": np.round(rng.normal(210, 35, n_rows), 1),
                "Cohort_Group": rng.choice(["Placebo", "Treatment_A", "Treatment_B"], n_rows, p=[0.33, 0.33, 0.34]),
            })
        elif template == "Customer Segmentation Analytics":
            df = pd.DataFrame({
                "Customer_ID": [f"CUST-{i:06d}" for i in range(n_rows)],
                "Age": rng.integers(18, 65, n_rows),
                "Region": rng.choice(["North America", "Europe", "Asia-Pacific", "Latin America"], n_rows),
                "Annual_Spend_USD": np.round(rng.exponential(1250, n_rows), 2),
                "Satisfaction_Score": rng.integers(1, 6, n_rows),
                "Active_Loyalty_Member": rng.choice([True, False], n_rows, p=[0.4, 0.6]),
            })
        elif template == "Financial Time Series":
            dates = pd.date_range(end=pd.Timestamp.today(), periods=n_rows, freq="D")
            df = pd.DataFrame({
                "Timestamp": dates,
                "Revenue_USD": np.round(rng.normal(15000, 2500, n_rows) + np.arange(n_rows) * 2.5, 2),
                "Operating_Cost_USD": np.round(rng.normal(9000, 1800, n_rows), 2),
                "Market_Region": rng.choice(["Global", "Domestic"], n_rows),
            })
        else:
            df = pd.DataFrame({
                "Metric_X": np.round(rng.normal(100, 15, n_rows), 2),
                "Metric_Y": np.round(rng.normal(50, 8, n_rows), 2),
                "Metric_Z": np.round(rng.uniform(0, 1, n_rows), 4),
                "Category_Tag": rng.choice(["Alpha", "Beta", "Gamma"], n_rows),
            })

        set_active_dataframe(df, f"synthetic_{template.lower().replace(' ', '_')}.csv")
        initialize_recipe_engine()
        st.session_state["transform_recipe"] = []
        st.session_state["dataset_schema_meta"] = {"fingerprint": dataset_fingerprint(df), "schema": schema_signature(df)}
        st.success(f"✅ Generated {n_rows:,} records for `{template}`.")
        st.dataframe(df.head(10), use_container_width=True)


def validate_readonly_sql(query: str):
    """Returns (ok, reason_or_cleaned_query). Only permits a single, read-only SELECT/WITH statement."""
    stripped = query.strip().rstrip(";").strip()
    if not stripped:
        return False, "Empty query."
    if ";" in stripped:
        return False, "Multiple statements are not permitted in this sandbox."
    first_word = stripped.split(None, 1)[0].upper()
    if first_word not in ("SELECT", "WITH"):
        return False, "Only SELECT / WITH (CTE) statements are permitted — this console is read-only."
    upper_q = stripped.upper()
    for kw in FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper_q):
            return False, f"Statement contains a restricted keyword: `{kw}`. This console cannot touch the filesystem, extensions, or anything outside the active in-memory dataset."
    return True, stripped


def render_explorer_tab():
    df = get_active_dataframe()
    section_header("📋 Dataset Explorer & Enterprise Export", "Inspect, query via a sandboxed DuckDB engine (if available), and export sanitized data assets.")

    if df is None:
        st.warning("No active dataset loaded.")
        return

    tab_view, tab_sql, tab_stats, tab_export = st.tabs(["👁️ Data Table", "⚡ DuckDB Query", "📈 Descriptive Statistics", "📥 Enterprise Export"])

    with tab_view:
        st.dataframe(df, use_container_width=True)

    with tab_sql:
        if DUCKDB_AVAILABLE:
            st.markdown("#### In-Memory SQL Query Engine (DuckDB) — Read-Only Sandbox")
            st.caption(f"SELECT-only. No filesystem/extension access. Results capped at {SQL_RESULT_ROW_CAP:,} rows.")
            sql_query = st.text_area("SQL Query Statement", value="SELECT * FROM df LIMIT 50", height=100, key="ent_sql_input")
            if st.button("🚀 Execute SQL Query", type="primary", key="ent_run_sql"):
                ok, msg_or_query = validate_readonly_sql(sql_query)
                if not ok:
                    st.error(f"🚫 Query rejected: {msg_or_query}")
                else:
                    try:
                        conn = duckdb.connect(database=":memory:")
                        conn.register("df", df)
                        result_df = conn.execute(msg_or_query).df()
                        conn.close()
                        truncated = len(result_df) > SQL_RESULT_ROW_CAP
                        if truncated:
                            result_df = result_df.head(SQL_RESULT_ROW_CAP)
                        st.success(f"✅ Query executed — returned {len(result_df):,} rows" + (f" (truncated to {SQL_RESULT_ROW_CAP:,})" if truncated else "") + ".")
                        st.dataframe(result_df, use_container_width=True)
                        render_export_buttons(result_df, base_name="sql_query_result")
                    except Exception as e:
                        st.error(f"SQL Execution Error: {e}")
        else:
            st.info("DuckDB engine package not detected in current environment.")

    with tab_stats:
        st.write(df.describe(include="all"))

    with tab_export:
        st.markdown("#### Export Cleaned Dataset Assets")
        render_export_buttons(df, base_name="enterprise_clean_dataset")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription(hub_id="data")

    setup_page("Enterprise Data Studio", "📁", initial_sidebar_state="expanded")

    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()

    hero_card(
        "📁 Enterprise Data Studio (Premium)",
        "Production-grade data management hub featuring secure schema management, sandboxed transformations, a replayable reproducible-recipe pipeline, dataset fingerprinting, and advanced anomaly detection.",
        badge_text="ENTERPRISE STUDIO • PREMIUM TIER",
    )

    render_dataset_context_banner()

    tabs = st.tabs([
        "📥 Ingestion Hub",
        "🔍 Quality & Remediation",
        "⚙️ Transform Studio",
        "🏷️ Schema Manager",
        "🎲 Synthetic Simulator",
        "📋 Explorer & SQL",
    ])

    with tabs[0]:
        render_ingestion_tab()
    with tabs[1]:
        render_quality_tab()
    with tabs[2]:
        render_transform_tab()
    with tabs[3]:
        render_variable_editor_tab()
    with tabs[4]:
        render_simulator_tab()
    with tabs[5]:
        render_explorer_tab()

    render_standard_footer("ENTERPRISE DATA STUDIO")


if __name__ == "__main__":
    main()