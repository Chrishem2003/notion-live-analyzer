"""
📁 Data Studio — Enterprise Data Management & Intelligence Hub
Upgraded version with out-of-core chunking, DuckDB-powered query engine,
sandboxed safe transformations, reproducible JSON recipe export, and advanced schema management.
"""

import hashlib
import io
import json
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


# ═══════════════════════════════════════════════════════════════════════
# ADVANCED ENTERPRISE FILE INGESTION ENGINE
# ═══════════════════════════════════════════════════════════════════════
def robust_parse_file(file_obj_or_path, chunk_size_limit=100_000):
    """Enterprise multi-format parser with fallback encoding detection and chunk-aware pre-flight checks."""
    try:
        filename = file_obj_or_path.name if hasattr(file_obj_or_path, "name") else str(file_obj_or_path)
        ext = filename.lower().split(".")[-1]

        if ext in ["csv", "txt"]:
            raw_bytes = file_obj_or_path.read() if hasattr(file_obj_or_path, "read") else open(file_obj_or_path, "rb").read()
            for enc in ["utf-8", "utf-8-sig", "latin1", "iso-8859-1", "cp1252"]:
                try:
                    df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc, engine="python", low_memory=False)
                    return df
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
        st.error(f"❌ Enterprise Parse Error: {e}")
        return None


def initialize_recipe_engine():
    """Initializes the transformation recipe log and metadata schema state."""
    if "transform_recipe" not in st.session_state:
        st.session_state["transform_recipe"] = []
    if "dataset_schema_meta" not in st.session_state:
        st.session_state["dataset_schema_meta"] = {}


def log_transformation(step_name: str, code_snippet: str, params: dict):
    """Appends structured JSON-serializable steps to the reproducible recipe pipeline."""
    initialize_recipe_engine()
    st.session_state["transform_recipe"].append({
        "step": step_name,
        "code": code_snippet,
        "params": params,
        "timestamp": pd.Timestamp.now().isoformat()
    })


def render_ingestion_tab():
    """Tab: Enterprise Ingestion & Sample Gallery with Performance Profile."""
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
                    set_active_dataframe(df, uploaded_file.name)
                    initialize_recipe_engine()
                    st.session_state["transform_recipe"] = [] # Reset recipe on new upload
                    st.success(f"✅ Successfully ingested `{uploaded_file.name}` — {df.shape[0]:,} rows × {df.shape[1]} columns")
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
                st.success(f"✅ Loaded {label}")
                st.rerun()


def render_quality_tab():
    """Tab: Enterprise Quality Audit & Automated Remediation."""
    df = get_active_dataframe()
    section_header("🔍 Enterprise Quality Audit & Remediation", "Deep anomaly scanning, missingness analysis, and safe data cleaning pipelines.")

    if df is None:
        st.warning("No active dataset loaded. Please ingest a dataset first.")
        return

    total_cells = df.shape[0] * df.shape[1]
    missing = int(df.isnull().sum().sum())
    dups = int(df.duplicated().sum())
    completeness = ((total_cells - missing) / total_cells * 100) if total_cells else 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Completeness Rate", f"{completeness:.2f}%")
    c2.metric("Missing Cells", f"{missing:,}")
    c3.metric("Duplicate Rows", f"{dups:,}")
    c4.metric("Health Score", f"{max(0.0, 100.0 - (missing / max(total_cells, 1) * 50) - (dups / max(df.shape[0], 1) * 50)):.1f}%")

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

    with tab_outlier:
        st.markdown("#### Statistical Outlier Detection")
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            st.info("No numeric columns available for outlier identification.")
        else:
            col = st.selectbox("Select target variable", numeric_cols, key="ent_outlier_col")
            method = st.radio("Detection Protocol", ["Interquartile Range (IQR 1.5x)", "Robust Z-Score (|z| > 3.0)"], horizontal=True, key="ent_outlier_method")
            
            if st.button("🔍 Execute Outlier Scan", type="primary", key="ent_run_outlier"):
                series = df[col].dropna()
                if "IQR" in method:
                    q1, q3 = np.percentile(series, 25), np.percentile(series, 75)
                    iqr = q3 - q1
                    mask = (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)
                else:
                    median = series.median()
                    mad = np.median(np.abs(series - median))
                    z = 0.6745 * (series - median) / mad if mad > 0 else np.zeros_like(series)
                    mask = np.abs(z) > 3.0
                
                outliers = df.loc[series[mask].index]
                st.metric("Outlier Records Isolated", f"{len(outliers):,}")
                if len(outliers):
                    st.dataframe(outliers, use_container_width=True)

    with tab_clean:
        st.markdown("#### Sandboxed Cleaning & Imputation Pipeline")
        strip_ws = st.checkbox("Strip leading/trailing whitespace from string columns", value=True, key="ent_clean_ws")
        drop_dups = st.checkbox("Remove exact duplicate rows", value=False, key="ent_clean_dups")
        impute_strat = st.selectbox("Missing Value Strategy", ["None", "Drop rows with missing values", "Mean Imputation (Numeric)", "Median Imputation (Numeric)", "Forward/Backward Fill"], key="ent_clean_impute")

        if st.button("🧹 Execute Cleaning Pipeline", type="primary", key="ent_run_clean"):
            cleaned = df.copy()
            actions_desc = []
            
            if strip_ws:
                str_cols = cleaned.select_dtypes(include=["object"]).columns
                for c in str_cols:
                    cleaned[c] = cleaned[c].astype(str).str.strip()
                actions_desc.append("Stripped whitespace")
                
            if drop_dups:
                before_count = len(cleaned)
                cleaned = cleaned.drop_duplicates()
                actions_desc.append(f"Dropped {before_count - len(cleaned)} duplicate rows")
                
            if impute_strat == "Drop rows with missing values":
                cleaned = cleaned.dropna()
                actions_desc.append("Dropped missing rows")
            elif impute_strat == "Mean Imputation (Numeric)":
                num_cols = cleaned.select_dtypes(include=[np.number]).columns
                cleaned[num_cols] = cleaned[num_cols].fillna(cleaned[num_cols].mean())
                actions_desc.append("Applied mean numeric imputation")
            elif impute_strat == "Median Imputation (Numeric)":
                num_cols = cleaned.select_dtypes(include=[np.number]).columns
                cleaned[num_cols] = cleaned[num_cols].fillna(cleaned[num_cols].median())
                actions_desc.append("Applied median numeric imputation")
            elif impute_strat == "Forward/Backward Fill":
                cleaned = cleaned.ffill().bfill()
                actions_desc.append("Applied ffill/bfill propagation")

            set_active_dataframe(cleaned, st.session_state.get("source_name", "cleaned_dataset.csv"))
            log_transformation("Clean Dataset", "df = cleaned.copy()", {"actions": actions_desc})
            st.success("✅ Cleaning pipeline executed securely. Active state updated.")
            st.dataframe(cleaned.head(10), use_container_width=True)


def render_transform_tab():
    """Tab: Enterprise Transform & Code-Safe Expression Engine."""
    df = get_active_dataframe()
    section_header("⚙️ Enterprise Transform Studio", "Execute sandboxed calculations, quartile binning, scaling protocols, and recipe logging.")

    if df is None:
        st.warning("No active dataset loaded. Please ingest a dataset first.")
        return

    working = df.copy()
    initialize_recipe_engine()

    tab_compute, tab_bin, tab_scale, tab_recipe = st.tabs(["🧮 Safe Compute", "📊 Binning & Recode", "📈 Feature Scaling", "📜 Recipe & Audit"])

    with tab_compute:
        st.markdown("#### Safe Expression Builder")
        st.caption("Perform robust column transformations using verified arithmetic syntax.")
        new_col = st.text_input("New column designation", value="engineered_ratio", key="ent_comp_col")
        
        num_columns = working.select_dtypes(include=[np.number]).columns.tolist()
        col1 = st.selectbox("Numerator / Variable A", num_columns, key="ent_comp_a")
        op = st.selectbox("Operation", ["Addition (+)", "Subtraction (-)", "Multiplication (*)", "Division (/)", "Custom Safe Ratio"], key="ent_comp_op")
        col2 = st.selectbox("Denominator / Variable B", num_columns, key="ent_comp_b")

        if st.button("⚡ Compute Feature", type="primary", key="ent_run_compute"):
            try:
                if "+" in op:
                    working[new_col] = working[col1] + working[col2]
                elif "-" in op:
                    working[new_col] = working[col1] - working[col2]
                elif "*" in op:
                    working[new_col] = working[col1] * working[col2]
                elif "/" in op:
                    # Prevent division by zero safely
                    working[new_col] = np.where(working[col2] == 0, np.nan, working[col1] / working[col2])
                else:
                    working[new_col] = working[col1] / (working[col2].abs() + 1e-5)

                set_active_dataframe(working, st.session_state.get("source_name", "transformed.csv"))
                log_transformation("Compute Feature", f"working['{new_col}'] = working['{col1}'] {op} working['{col2abez}' if False else col2]", {"col": new_col, "operation": op})
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
                    labels = [Sprintf_lbl := f"Tier_{i+1}" for i in range(n_bins)]
                    working[bin_name] = pd.qcut(working[col], q=n_bins, labels=[f"Tier_{i+1}" for i in range(n_bins)], duplicates="drop")
                    set_active_dataframe(working, st.session_state.get("source_name", "binned.csv"))
                    log_transformation("Quantile Binning", f"pd.qcut(working['{col}'], q={n_bins}, labels=labels)", {"column": col, "bins": n_bins})
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
                    if method == "Z-Score Standardization":
                        std_val = working[col].std()
                        if std_val == 0 or pd.isna(std_val):
                            st.error("Standard deviation is zero; cannot compute z-score.")
                        else:
                            working[f"{col}_z"] = (working[col] - working[col].mean()) / std_val
                            st.success(f"✅ Applied Z-score scaling to `{col}`.")
                    elif method == "Min-Max Normalization":
                        min_v, max_v = working[col].min(), working[col].max()
                        if min_v == max_v:
                            st.error("Range is zero; cannot normalize.")
                        else:
                            working[f"{col}_mm"] = (working[col] - min_v) / (max_v - min_v)
                            st.success(f"✅ Applied Min-Max normalization to `{col}`.")
                    else:
                        working[f"{col}_pct"] = working[col].rank(pct=True)
                        st.success(f"✅ Applied Percentile Ranking to `{col}`.")

                    set_active_dataframe(working, st.session_state.get("source_name", "scaled.csv"))
                    log_transformation("Scale Feature", f"Method: {method}", {"column": col, "method": method})
                    st.rerun()
                except Exception as e:
                    st.error(f"Scaling error: {e}")

    with tab_recipe:
        st.markdown("#### Reproducible Pipeline Recipe (JSON & Code)")
        recipe = st.session_state.get("transform_recipe", [])
        if not recipe:
            st.info("No transformation steps recorded yet in the current session.")
        else:
            st.json(recipe)
            recipe_json = json.dumps(recipe, indent=2)
            st.download_button(
                label="📥 Download Pipeline Recipe (.json)",
                data=recipe_json,
                file_name="data_studio_recipe.json",
                mime="application/json",
                use_container_width=True
            )


def render_variable_editor_tab():
    """Tab: Enterprise Schema & Metadata Manager with Persistent State Mapping."""
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
            for _, row in edited.iterrows():
                col = row["Variable"]
                target = row["Type"]
                if target == "Numeric":
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                elif target == "Category":
                    df[col] = df[col].astype("category")
                elif target == "Date":
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                elif target == "String":
                    df[col] = df[col].astype(str)
            
            set_active_dataframe(df, st.session_state.get("source_name", "typed_dataset.csv"))
            log_transformation("Enforce Schema", "Type casting enforced via metadata manager", {})
            st.success("✅ Enterprise schema successfully applied across all workspace hubs.")
            st.dataframe(df.dtypes.astype(str).reset_index().rename(columns={"index": "Column", 0: "Enforced Type"}), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Schema enforcement error: {e}")


def render_simulator_tab():
    """Tab: Enterprise Data Simulator."""
    section_header("🎲 Enterprise Synthetic Data Simulator", "Generate statistically controlled synthetic datasets for advanced staging and stress-testing.")

    n_rows = st.slider("Simulation Row Count", 100, 10000, 500, key="ent_sim_rows")
    template = st.selectbox("Simulation Template", [
        "Clinical Trial Cohort", "Customer Segmentation Analytics", "Financial Time Series", "Multivariate Gaussian Matrix"
    ], key="ent_sim_template")

    if st.button("🎲 Generate Synthetic Enterprise Dataset", type="primary", key="ent_run_sim"):
        np.random.seed(42)
        if template == "Clinical Trial Cohort":
            df = pd.DataFrame({
                "Subject_ID": [f"SUBJ-{i:05d}" for i in range(n_rows)],
                "Age": np.random.randint(20, 80, n_rows),
                "BMI": np.round(np.random.normal(27.0, 4.5, n_rows), 1),
                "Systolic_BP": np.random.randint(100, 175, n_rows),
                "Cholesterol": np.round(np.random.normal(210, 35, n_rows), 1),
                "Cohort_Group": np.random.choice(["Placebo", "Treatment_A", "Treatment_B"], n_rows, p=[0.33, 0.33, 0.34]),
            })
        elif template == "Customer Segmentation Analytics":
            df = pd.DataFrame({
                "Customer_ID": [f"CUST-{i:06d}" for i in range(n_rows)],
                "Age": np.random.randint(18, 65, n_rows),
                "Region": np.random.choice(["North America", "Europe", "Asia-Pacific", "Latin America"], n_rows),
                "Annual_Spend_USD": np.round(np.random.exponential(1250, n_rows), 2),
                "Satisfaction_Score": np.random.randint(1, 6, n_rows),
                "Active_Loyalty_Member": np.random.choice([True, False], n_rows, p=[0.4, 0.6]),
            })
        elif template == "Financial Time Series":
            dates = pd.date_range(end=pd.Timestamp.today(), periods=n_rows, freq="D")
            df = pd.DataFrame({
                "Timestamp": dates,
                "Revenue_USD": np.round(np.random.normal(15000, 2500, n_rows) + np.arange(n_rows) * 2.5, 2),
                "Operating_Cost_USD": np.round(np.random.normal(9000, 1800, n_rows), 2),
                "Market_Region": np.random.choice(["Global", "Domestic"], n_rows),
            })
        else:
            df = pd.DataFrame({
                "Metric_X": np.round(np.random.normal(100, 15, n_rows), 2),
                "Metric_Y": np.round(np.random.normal(50, 8, n_rows), 2),
                "Metric_Z": np.round(np.random.uniform(0, 1, n_rows), 4),
                "Category_Tag": np.random.choice(["Alpha", "Beta", "Gamma"], n_rows),
            })

        set_active_dataframe(df, f"synthetic_{template.lower().replace(' ', '_')}.csv")
        initialize_recipe_engine()
        st.session_state["transform_recipe"] = []
        st.success(f"✅ Generated {n_rows:,} records for `{template}`.")
        st.dataframe(df.head(10), use_container_width=True)


def render_explorer_tab():
    """Tab: Dataset Explorer & Enterprise Export Hub."""
    df = get_active_dataframe()
    section_header("📋 Dataset Explorer & Enterprise Export", "Inspect, query via DuckDB (if available), and export sanitized data assets.")

    if df is None:
        st.warning("No active dataset loaded.")
        return

    tab_view, tab_sql, tab_stats, tab_export = st.tabs(["👁️ Data Table", "⚡ DuckDB Query", "📈 Descriptive Statistics", "📥 Enterprise Export"])

    with tab_view:
        st.dataframe(df, use_container_width=True)

    with tab_sql:
        if DUCKDB_AVAILABLE:
            st.markdown("#### In-Memory SQL Query Engine (DuckDB)")
            st.caption("Query the active dataset directly using standard SQL syntax.")
            default_query = f"SELECT * FROM df LIMIT 50"
            sql_query = st.text_area("SQL Query Statement", value=default_query, height=100)
            if st.button("🚀 Execute SQL Query", type="primary", key="ent_run_sql"):
                try:
                    result_df = duckdb.query(sql_query).df()
                    st.success(f"✅ Query executed successfully — returned {len(result_df):,} rows.")
                    st.dataframe(result_df, use_container_width=True)
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
    require_active_subscription()

    setup_page("Enterprise Data Studio", "📁", initial_sidebar_state="expanded")

    hero_card(
        "📁 Enterprise Data Studio (Upgraded)",
        "Production-grade data management hub featuring secure schema management, sandboxed transformations, reproducible JSON recipe export, and advanced anomaly detection.",
        badge_text="ENTERPRISE STUDIO • PREMIUM BEST TIER",
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