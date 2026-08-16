"""
📁 Data Studio — Consolidated Data Management Hub
Consolidates old pages: 1 (File Analyzer), 7 (Variable View), 8 (Data Transformer),
13/14 (Data Quality), 37/38 (Chart Data Extractor), 14 (Data Simulator).
"""

import hashlib
import io

import numpy as np
import pandas as pd
import streamlit as st

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


# ═══════════════════════════════════════════════════════════════════════
# FILE INGESTION ENGINE
# ═══════════════════════════════════════════════════════════════════════
def robust_parse_file(file_obj_or_path):
    """Robust multi-format document parser supporting CSV, Excel, JSON, SPSS, SAS, STATA, Parquet."""
    try:
        filename = file_obj_or_path.name if hasattr(file_obj_or_path, "name") else str(file_obj_or_path)
        ext = filename.lower().split(".")[-1]

        if ext in ["csv", "txt"]:
            raw_bytes = file_obj_or_path.read() if hasattr(file_obj_or_path, "read") else open(file_obj_or_path, "rb").read()
            for enc in ["utf-8", "utf-8-sig", "latin1", "iso-8859-1", "cp1252"]:
                try:
                    return pd.read_csv(io.BytesIO(raw_bytes), encoding=enc, engine="python", low_memory=False)
                except Exception:
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
                    import tempfile
                    suffix_map = {"sav": ".sav", "sas7bdat": ".sas7bdat", "dta": ".dta"}
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix_map[ext]) as tmp:
                        tmp.write(file_obj_or_path.read())
                        path = tmp.name
                if ext == "sav":
                    df, _ = pyreadstat.read_sav(path)
                elif ext == "sas7bdat":
                    df, _ = pyreadstat.read_sas7bdat(path)
                else:
                    df, _ = pyreadstat.read_dta(path)
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
        st.error(f"❌ Parse error: {e}")
        return None


def render_ingestion_tab():
    """Tab: File ingestion + sample data gallery."""
    section_header("📥 Data Ingestion & Sample Gallery", "Upload multi-format files or load curated sample datasets.")

    col_up, col_sample = st.columns([1.4, 1])

    with col_up:
        st.markdown("#### 📁 Upload Data File")
        uploaded_file = st.file_uploader(
            "Choose a data file (CSV, Excel, JSON, SPSS, SAS, STATA, Parquet)",
            type=["csv", "xlsx", "xls", "json", "sav", "sas7bdat", "dta", "parquet", "pkl", "txt"],
            key="data_studio_uploader",
        )
        if uploaded_file is not None:
            with st.spinner(f"Parsing '{uploaded_file.name}'..."):
                df = robust_parse_file(uploaded_file)
                if df is not None and not df.empty:
                    set_active_dataframe(df, uploaded_file.name)
                    st.success(f"✅ Loaded `{uploaded_file.name}` — {df.shape[0]:,} rows × {df.shape[1]} cols")
                    st.dataframe(df.head(10), use_container_width=True)

    with col_sample:
        st.markdown("#### 🎲 Sample Data Gallery")
        st.caption("Curated sample datasets to explore each hub's capabilities.")
        sample_kinds = {
            "Clinical Cohort (150 patients)": "clinical",
            "Marketing / Customer (200)": "marketing",
            "Sales Transactions (300)": "sales",
            "Genomic Expression (100)": "genomic",
            "Survey Responses (250)": "survey",
            "Research Cohort (250)": "research",
        }
        for label, kind in sample_kinds.items():
            if st.button(label, use_container_width=True, key=f"smp_{kind}"):
                set_active_dataframe(generate_sample_dataset(kind), f"{kind}_sample.csv")
                st.rerun()


def render_quality_tab():
    """Tab: Data quality audit + cleaning."""
    df = get_active_dataframe()
    section_header("🔍 Data Quality Audit & Cleaning", "Completeness, uniqueness, anomaly detection, and remediation pipelines.")

    if df is None:
        st.warning("No active dataset. Load one in the Ingestion tab first.")
        return

    # Health metrics
    total_cells = df.shape[0] * df.shape[1]
    missing = int(df.isnull().sum().sum())
    dups = int(df.duplicated().sum())
    completeness = ((total_cells - missing) / total_cells * 100) if total_cells else 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Completeness", f"{completeness:.1f}%")
    c2.metric("Missing Cells", f"{missing:,}")
    c3.metric("Duplicate Rows", f"{dups:,}")
    c4.metric("Quality Score", f"{max(0, 100 - missing / max(total_cells,1)*100 - dups):.1f}")

    tab_audit, tab_outlier, tab_clean = st.tabs(["📊 Quality Audit", "⚠️ Outlier Detection", "🛠️ Auto-Clean"])

    with tab_audit:
        st.markdown("#### Schema & Missingness Audit")
        schema = pd.DataFrame({
            "Column": df.columns,
            "Type": df.dtypes.astype(str),
            "Null Count": df.isnull().sum().values,
            "Null %": (df.isnull().mean() * 100).round(2).values,
            "Unique": df.nunique().values,
        })
        st.dataframe(schema, use_container_width=True, hide_index=True)

    with tab_outlier:
        st.markdown("#### Outlier & Anomaly Detection")
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            st.info("No numeric columns available for outlier detection.")
        else:
            col = st.selectbox("Select numeric feature", numeric_cols, key="outlier_col_ds")
            method = st.radio("Method", ["IQR (1.5×)", "Z-Score (|z|>3)"], horizontal=True, key="outlier_method_ds")
            if st.button("🔍 Run Outlier Scan", type="primary", key="run_outlier_ds"):
                series = df[col].dropna()
                if method.startswith("IQR"):
                    q1, q3 = np.percentile(series, 25), np.percentile(series, 75)
                    iqr = q3 - q1
                    mask = (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)
                else:
                    z = np.abs((series - series.mean()) / series.std()) if series.std() > 0 else 0
                    mask = z > 3
                outliers = df.loc[series[mask].index]
                st.metric("Outliers Detected", f"{len(outliers):,}")
                if len(outliers):
                    st.dataframe(outliers, use_container_width=True)

    with tab_clean:
        st.markdown("#### Automated Cleaning Pipeline")
        strip_ws = st.checkbox("Strip whitespace from strings", value=True, key="clean_ws_ds")
        drop_dups = st.checkbox("Drop duplicate rows", value=False, key="clean_dup_ds")
        impute = st.selectbox("Missing value strategy", ["None", "Drop rows", "Mean (numeric)", "Median (numeric)", "Forward-fill"], key="clean_imp_ds")

        if st.button("🧹 Execute Cleaning Pipeline", type="primary", key="run_clean_ds"):
            cleaned = df.copy()
            if strip_ws:
                for c in cleaned.select_dtypes(include=["object"]).columns:
                    cleaned[c] = cleaned[c].astype(str).str.strip()
            if drop_dups:
                cleaned = cleaned.drop_duplicates()
            if impute == "Drop rows":
                cleaned = cleaned.dropna()
            elif impute == "Mean (numeric)":
                num = cleaned.select_dtypes(include=[np.number]).columns
                cleaned[num] = cleaned[num].fillna(cleaned[num].mean())
            elif impute == "Median (numeric)":
                num = cleaned.select_dtypes(include=[np.number]).columns
                cleaned[num] = cleaned[num].fillna(cleaned[num].median())
            elif impute == "Forward-fill":
                cleaned = cleaned.ffill().bfill()

            set_active_dataframe(cleaned, st.session_state.get("source_name", "cleaned_dataset.csv"))
            st.success("✅ Cleaning pipeline executed. Active dataset updated.")
            st.dataframe(cleaned.head(10), use_container_width=True)


def render_transform_tab():
    """Tab: SPSS-style transformations."""
    df = get_active_dataframe()
    section_header("⚙️ Transform & Engineering Studio", "Compute expressions, bin values, standardize, and rank variables.")

    if df is None:
        st.warning("No active dataset. Load one in the Ingestion tab first.")
        return

    working = df.copy()
    if "transform_log_ds" not in st.session_state:
        st.session_state["transform_log_ds"] = []

    tab_compute, tab_bin, tab_scale, tab_log = st.tabs(["🧮 Compute", "📊 Bin/Recode", "📈 Rank/Standardize", "📜 Audit Log"])

    with tab_compute:
        st.markdown("#### Mathematical Expression Compute")
        new_col = st.text_input("New column name", value="computed_metric", key="compute_name_ds")
        expr = st.text_input("Expression (pandas eval)", value="Income_Level / Age", key="compute_expr_ds")
        st.caption("Available columns: " + ", ".join(list(working.columns)))
        if st.button("⚡ Compute Expression", type="primary", key="run_compute_ds"):
            try:
                working[new_col] = working.eval(expr)
                st.session_state["transform_log_ds"].append(f"Computed '{new_col}' = {expr}")
                set_active_dataframe(working, st.session_state.get("source_name", "transformed.csv"))
                st.success(f"✅ Column '{new_col}' added.")
                st.rerun()
            except Exception as e:
                st.error(f"Computation error: {e}")

    with tab_bin:
        st.markdown("#### Quantile Binning")
        numeric_cols = working.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            st.info("No numeric columns available.")
        else:
            col = st.selectbox("Select variable to bin", numeric_cols, key="bin_col_ds")
            n_bins = st.slider("Number of bins", 2, 10, 4, key="bin_n_ds")
            bin_name = st.text_input("Binned column name", value=f"{col}_bin", key="bin_name_ds")
            if st.button("📊 Generate Bins", type="primary", key="run_bin_ds"):
                try:
                    labels = [f"Tier_{i+1}" for i in range(n_bins)]
                    working[bin_name] = pd.qcut(working[col], q=n_bins, labels=labels, duplicates="drop")
                    st.session_state["transform_log_ds"].append(f"Binned '{col}' into {n_bins} tiers as '{bin_name}'")
                    set_active_dataframe(working, st.session_state.get("source_name", "binned.csv"))
                    st.success(f"✅ Binned variable '{bin_name}' created.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Binning error: {e}")

    with tab_scale:
        st.markdown("#### Z-Score / Min-Max / Percentile Rank")
        numeric_cols = working.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            st.info("No numeric columns available.")
        else:
            col = st.selectbox("Select variable", numeric_cols, key="scale_col_ds")
            method = st.selectbox("Method", ["Z-Score", "Min-Max", "Percentile Rank"], key="scale_method_ds")
            if st.button("📈 Apply Scaling", type="primary", key="run_scale_ds"):
                if method == "Z-Score":
                    working[f"{col}_z"] = (working[col] - working[col].mean()) / (working[col].std() if working[col].std() else 1)
                elif method == "Min-Max":
                    working[f"{col}_mm"] = (working[col] - working[col].min()) / ((working[col].max() - working[col].min()) if working[col].max() != working[col].min() else 1)
                else:
                    working[f"{col}_pct"] = working[col].rank(pct=True)
                st.session_state["transform_log_ds"].append(f"Applied {method} on '{col}'")
                set_active_dataframe(working, st.session_state.get("source_name", "scaled.csv"))
                st.success(f"✅ {method} applied.")
                st.rerun()

    with tab_log:
        st.markdown("#### Transformation Audit Trail")
        log = st.session_state.get("transform_log_ds", [])
        if not log:
            st.info("No transformations logged yet.")
        for i, step in enumerate(log, 1):
            st.markdown(f"**{i}.** {step}")


def render_variable_editor_tab():
    """Tab: SPSS-style variable metadata editor."""
    df = get_active_dataframe()
    section_header("🏷️ Variable View & Metadata Editor", "Edit variable labels, types, and measurement levels.")

    if df is None:
        st.warning("No active dataset. Load one in the Ingestion tab first.")
        return

    meta_records = []
    for col in df.columns:
        is_num = pd.api.types.is_numeric_dtype(df[col])
        meta_records.append({
            "Variable": col,
            "Type": "Numeric" if is_num else "String",
            "Measurement": "Scale" if is_num and df[col].nunique() > 10 else "Nominal",
            "Missing": int(df[col].isnull().sum()),
            "Unique": int(df[col].nunique()),
        })
    meta_df = pd.DataFrame(meta_records)

    edited = st.data_editor(
        meta_df,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Type": st.column_config.SelectboxColumn("Type", options=["Numeric", "String", "Category", "Date"]),
            "Measurement": st.column_config.SelectboxColumn("Measurement", options=["Scale", "Nominal", "Ordinal"]),
        },
        hide_index=True,
        key="var_editor_ds",
    )

    if st.button("🚀 Apply Variable Metadata & Enforce Types", type="primary", key="apply_var_ds"):
        try:
            for _, row in edited.iterrows():
                col = row["Variable"]
                target = row["Type"]
                if target == "Numeric":
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                elif target == "Category":
                    df[col] = df[col].astype("category")
                elif target == "Date":
                    df[col] = pd.to_datetime(df[col], errors="coerce")
            set_active_dataframe(df, st.session_state.get("source_name", "typed_dataset.csv"))
            st.success("✅ Variable types enforced across all hubs.")
            st.dataframe(df.dtypes.astype(str).reset_index().rename(columns={"index": "Column", 0: "Type"}), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error applying types: {e}")


def render_simulator_tab():
    """Tab: Data simulator."""
    section_header("🎲 Data Simulator", "Generate synthetic datasets with controlled parameters.")

    n_rows = st.slider("Number of rows", 50, 1000, 200, key="sim_rows_ds")
    col_type = st.selectbox("Simulation template", [
        "Clinical Trial", "Customer Analytics", "Time Series", "Random Gaussian",
    ], key="sim_template_ds")

    if st.button("🎲 Generate Synthetic Dataset", type="primary", key="run_sim_ds"):
        np.random.seed(42)
        if col_type == "Clinical Trial":
            df = pd.DataFrame({
                "Patient_ID": [f"PT-{i:04d}" for i in range(n_rows)],
                "Age": np.random.randint(18, 85, n_rows),
                "BMI": np.round(np.random.normal(26.5, 5.0, n_rows), 1),
                "Systolic_BP": np.random.randint(90, 180, n_rows),
                "Glucose": np.round(np.random.normal(105, 25, n_rows), 1),
                "Group": np.random.choice(["Control", "Treatment"], n_rows),
            })
        elif col_type == "Customer Analytics":
            df = pd.DataFrame({
                "Customer_ID": [f"C-{i:05d}" for i in range(n_rows)],
                "Age": np.random.randint(18, 70, n_rows),
                "Region": np.random.choice(["North", "South", "East", "West"], n_rows),
                "Spending": np.round(np.random.exponential(120, n_rows), 2),
                "Satisfaction": np.random.randint(1, 6, n_rows),
            })
        elif col_type == "Time Series":
            dates = pd.date_range(end=pd.Timestamp.today(), periods=n_rows, freq="D")
            df = pd.DataFrame({
                "Date": dates,
                "Sales": np.round(np.random.normal(1000, 200, n_rows) + np.arange(n_rows) * 0.5, 2),
                "Cost": np.round(np.random.normal(600, 150, n_rows), 2),
                "Region": np.random.choice(["US", "EU", "ASIA", "AFR"], n_rows),
            })
        else:
            df = pd.DataFrame({
                "Var_A": np.round(np.random.normal(50, 10, n_rows), 2),
                "Var_B": np.round(np.random.normal(30, 5, n_rows), 2),
                "Var_C": np.round(np.random.uniform(0, 100, n_rows), 2),
                "Category": np.random.choice(["X", "Y", "Z"], n_rows),
            })
        set_active_dataframe(df, f"simulated_{col_type.lower().replace(' ', '_')}.csv")
        st.success(f"✅ Generated {n_rows} rows of {col_type} data.")
        st.dataframe(df.head(10), use_container_width=True)


def render_explorer_tab():
    """Tab: Dataset explorer + preview + export."""
    df = get_active_dataframe()
    section_header("📋 Dataset Explorer & Export", "Preview, filter, and export the active dataset.")

    if df is None:
        st.warning("No active dataset to explore.")
        return

    tab_view, tab_stats, tab_export = st.tabs(["👁️ Data Table", "📈 Descriptive Stats", "📥 Export"])

    with tab_view:
        st.dataframe(df, use_container_width=True)

    with tab_stats:
        st.write(df.describe(include="all"))

    with tab_export:
        st.markdown("#### Download Active Dataset")
        render_export_buttons(df, base_name="active_dataset")


def main():
    setup_page("Data Studio", "📁", initial_sidebar_state="expanded")

    hero_card(
        "📁 Enterprise Data Studio",
        "Consolidated data management hub: ingest multi-format files, audit quality, transform variables, edit metadata, simulate datasets, and export clean data.",
        badge_text="DATA STUDIO • CONSOLIDATED HUB",
    )

    render_dataset_context_banner()

    tabs = st.tabs([
        "📥 Ingestion",
        "🔍 Quality & Clean",
        "⚙️ Transform",
        "🏷️ Variable Editor",
        "🎲 Simulator",
        "📋 Explorer & Export",
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

    render_standard_footer("DATA STUDIO")


if __name__ == "__main__":
    main()

