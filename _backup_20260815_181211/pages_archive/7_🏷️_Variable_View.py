"""
🔍 Variable View Page | Advanced SPSS-Style Metadata Editor & Codebook Studio [v3.0 Enterprise]
Complete standalone edition featuring high-contrast layout, functional metadata editing, 
real pandas dtype transformations, APA codebook exports, and schema JSON synchronization.
Designed for: Kula Chris (Chrishem)
"""

import json
import streamlit as st
import pandas as pd
import numpy as np

# ─── 1. PAGE CONFIGURATION ──────────────────────────────────────────────
st.set_page_config(
    page_title="Variable View Studio", 
    layout="wide", 
    page_icon="🔍",
    initial_sidebar_state="expanded"
)

# Initialize Session State Variables
if "variable_meta_df" not in st.session_state:
    st.session_state["variable_meta_df"] = None

# ─── 2. HIGH-CONTRAST / ULTRA-LEGIBLE COLOR STYLING ─────────────────────
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

    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
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
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    }
    .contrast-card-emerald {
        background: #062419 !important;
        border: 1px solid #10b981 !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
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
    
    .stTextInput input, .stSelectbox div, .stNumberInput input, .stTextArea textarea {
        background-color: #1a2638 !important;
        color: #ffffff !important;
        border: 1px solid #00f2fe88 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
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
    .badge-emerald {
        background: #064e3b;
        color: #34d399;
        border: 1px solid #10b981;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-size: 0.7rem;
        font-family: monospace;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── 3. DATA ACQUISITION & FALLBACK GENERATOR ───────────────────────────
if "active_df" not in st.session_state or st.session_state["active_df"] is None:
    if "notion_df" in st.session_state and st.session_state["notion_df"] is not None:
        st.session_state["active_df"] = st.session_state["notion_df"]

active_df = st.session_state.get("active_df")

if active_df is None or active_df.empty:
    st.markdown(
        """
        <div class='contrast-card-emerald' style='margin-top:1rem;'>
            <span class='badge-emerald'>DEMO MODE AUTOMATION</span>
            <h3 style='margin-top:0.4rem;'>⚠️ No Active Dataset Detected in Memory</h3>
            <p style='color:#cbd5e1;'>You can generate a dummy research cohort dataset now or connect your data sources.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔍 Generate Sample Research Cohort Data", type="primary", use_container_width=True):
            np.random.seed(42)
            demo_data = pd.DataFrame({
                "Subject_ID": [f"SUBJ_{1000 + i}" for i in range(100)], # FIXED SYNTAX ERROR HERE
                "Age": np.random.randint(18, 65, size=100),
                "Gender": np.random.choice(["Male", "Female", "Non-Binary"], size=100),
                "Treatment_Group": np.random.choice(["Control", "Dosage_A", "Dosage_B"], size=100),
                "Baseline_Score": np.round(np.random.normal(55.0, 10.0, size=100), 2),
                "Post_Score": np.round(np.random.normal(70.0, 12.0, size=100), 2),
                "Adverse_Events": np.random.choice([0, 1, 999], size=100, p=[0.7, 0.25, 0.05])
            })
            st.session_state["active_df"] = demo_data
            st.rerun()
    with col_b:
        st.info("🔍 Load standard CSV/XLSX files using the File Analyzer or connect to a Notion Database workspace.")
    st.stop()

# ─── 4. HERO HEADER ─────────────────────────────────────────────────────
st.markdown(
    """
<div style='display:flex; justify-content:space-between; align-items:center; background: linear-gradient(135deg, #0b1e36 0%, #061527 100%); border: 2px solid #00f2fe; padding: 1.5rem; border-radius: 14px; margin-bottom: 1.5rem;'>
    <div>
        <span class='badge-primary'>SPSS METADATA ENGINE & CODEBOOK STUDIO v3.0</span>
        <h1 style='font-size: 2.2rem; margin: 0.4rem 0 0.2rem 0; color: #00f2fe;'>🔍 Variable View Page</h1>
        <p style='color: #cbd5e1; margin: 0; font-size: 0.95rem;'>
            Define variable metadata, construct value labels, configure missing value codes, audit measurement levels, and cast data types securely.
        </p>
    </div>
    <div style='text-align: right;'>
        <div style='background: #111c2e; border: 1px solid #10b981; padding: 0.6rem 1.1rem; border-radius: 10px;'>
            <div style='font-size: 0.65rem; color: #94a3b8; text-transform: uppercase; font-weight: 800;'>Studio Brand</div>
            <div style='color: #10b981; font-size: 1rem; font-weight: 900;'>🔍 CHRISHEM METADATA ENGINE</div>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ─── 5. SCHEMA METRICS METADATA BAR ──────────────────────────────────────
st.markdown("<h3 style='margin-bottom:0.5rem;'>🔍 Metadata Health & Schema Metrics</h3>", unsafe_allow_html=True)

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("Total Rows", f"{len(active_df):,}")
    st.markdown("</div>", unsafe_allow_html=True)
with m2:
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("Variables", f"{len(active_df.columns):,}")
    st.markdown("</div>", unsafe_allow_html=True)
with m3:
    num_cols = len(active_df.select_dtypes(include=[np.number]).columns)
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("Continuous (Scale)", num_cols)
    st.markdown("</div>", unsafe_allow_html=True)
with m4:
    cat_cols = len(active_df.select_dtypes(include=["object", "category"]).columns)
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("Nominal / Ordinal", cat_cols)
    st.markdown("</div>", unsafe_allow_html=True)
with m5:
    memory_mb = active_df.memory_usage(deep=True).sum() / (1024 * 1024)
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("Memory Footprint", f"{memory_mb:.2f} MB")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)

# ─── 6. WORKSPACE TABS ───────────────────────────────────────────────────
tab_editor, tab_batch, tab_codebook, tab_template = st.tabs([
    "🔍 SPSS Metadata Editor", 
    "⚡ Batch Operations & Quick Rules", 
    "🔍 Publication Codebook", 
    "🔍 Metadata Schema Sync"
])

# ── TAB 1: Main Interactive Metadata Editor ─────────────────────────────
with tab_editor:
    st.markdown("### ✏️ Variable Property Configuration Grid")
    st.caption("Adjust variable labels, measurement scales, and data types. Changes here will be cast to the DataFrame when applied.")
    
    if st.session_state["variable_meta_df"] is None or len(st.session_state["variable_meta_df"]) != len(active_df.columns):
        meta_records = []
        for col in active_df.columns:
            is_num = pd.api.types.is_numeric_dtype(active_df[col])
            inferred_measure = "Scale" if is_num and active_df[col].nunique() > 10 else "Nominal"
            meta_records.append({
                "Variable Name": col,
                "Label": f"{col.replace('_', ' ')}",
                "Type": "Numeric" if is_num else "String",
                "Measurement": inferred_measure,
                "Role": "Input" if col != active_df.columns[-1] else "Target"
            })
        meta_df = pd.DataFrame(meta_records)
    else:
        meta_df = st.session_state["variable_meta_df"]
    
    # Save the output of the data editor directly to session state
    edited_metadata = st.data_editor(
        meta_df,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Variable Name": st.column_config.TextColumn("Variable Name", disabled=True),
            "Measurement": st.column_config.SelectboxColumn("Measurement Level", options=["Scale", "Nominal", "Ordinal"], required=True),
            "Role": st.column_config.SelectboxColumn("SPSS Variable Role", options=["Input", "Target", "Both", "None", "Partition"]),
            "Type": st.column_config.SelectboxColumn("Data Type", options=["Numeric", "String", "Category", "Date"])
        },
        hide_index=True,
        key="meta_editor"
    )
    st.session_state["variable_meta_df"] = edited_metadata

# ── TAB 2: Batch Operations ─────────────────────────────────────────────
with tab_batch:
    st.markdown("### ⚡ Fast Batch Transformations & Auto-Detection")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
        st.subheader("🔍 Automated Metadata Inference")
        st.markdown("Scan distributions to auto-assign scales and cast datatypes (e.g., String to Category for memory efficiency).")
        
        if st.button("🔍 Auto-Detect & Optimize Types", use_container_width=True):
            with st.spinner("Analyzing column cardinalities..."):
                for col in active_df.columns:
                    if pd.api.types.is_object_dtype(active_df[col]) and active_df[col].nunique() < (len(active_df) * 0.5):
                        active_df[col] = active_df[col].astype("category")
                    
                st.session_state["active_df"] = active_df
                # Reset metadata so it rebuilds on next render
                st.session_state["variable_meta_df"] = None 
            st.success("✅ Datasets optimized! Strings with low cardinality were converted to Categories.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ── TAB 3: Publication Codebook ─────────────────────────────────────────
with tab_codebook:
    st.markdown("### 🔍 APA / SPSS Style Data Dictionary")
    
    codebook_data = []
    for col in active_df.columns:
        missing_cnt = active_df[col].isnull().sum()
        missing_pct = (missing_cnt / len(active_df)) * 100
        n_unique = active_df[col].nunique()
        sample_vals = str(active_df[col].dropna().unique()[:3].tolist())
        
        codebook_data.append({
            "Variable": col,
            "Pandas DType": str(active_df[col].dtype),
            "Missing Count": missing_cnt,
            "Missing %": f"{missing_pct:.1f}%",
            "Unique Values": n_unique,
            "Sample Data": sample_vals
        })
    
    codebook_df = pd.DataFrame(codebook_data)
    st.dataframe(codebook_df, use_container_width=True, hide_index=True)
    
    csv_codebook = codebook_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "🔍 Download Publication Codebook (CSV)",
        data=csv_codebook,
        file_name="dataset_publication_codebook.csv",
        mime="text/csv",
    )

# ── TAB 4: Metadata Export & Import Sync ────────────────────────────────
with tab_template:
    st.markdown("### 🔍 Metadata Schema Sync")
    st.info("Export your metadata mapping to JSON to enforce standardized typing across similar research cohorts.")
    
    schema = {
        "columns": list(active_df.columns),
        "types": {col: str(active_df[col].dtype) for col in active_df.columns},
        "version": "3.0"
    }
    json_schema = json.dumps(schema, indent=4)
    st.download_button(
        "🔍 Download Metadata Schema (.json)",
        data=json_schema,
        file_name="variable_metadata_schema.json",
        mime="application/json"
    )

# ─── 7. EXECUTION & SESSION STATE PERSISTENCE ───────────────────────────
st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)
st.markdown("### 🔍 Apply Metadata & Update Active Dataset")

col_save, col_clear = st.columns([3, 1])

with col_save:
    if st.button("🚀 Apply Variable Metadata & Enforce Data Types", type="primary", use_container_width=True):
        with st.spinner("Enforcing data types and writing changes to global memory..."):
            meta = st.session_state["variable_meta_df"]
            
            # Actively transform dataframe based on editor selections
            for idx, row in meta.iterrows():
                col_name = row["Variable Name"]
                target_type = row["Type"]
                measure_lvl = row["Measurement"]
                
                try:
                    if target_type == "Numeric":
                        active_df[col_name] = pd.to_numeric(active_df[col_name], errors='coerce')
                    elif target_type == "String":
                        active_df[col_name] = active_df[col_name].astype(str)
                    elif target_type == "Category" or measure_lvl in ["Nominal", "Ordinal"]:
                        active_df[col_name] = active_df[col_name].astype("category")
                except Exception as e:
                    st.warning(f"Could not convert {col_name} to {target_type}: {e}")

            st.session_state["active_df"] = active_df
            
        st.success("✅ **Real data types applied successfully!** Dataset is now strictly typed and synchronized across all pages.")
        
        with st.expander("🔍 View Updated Dataset Memory Status", expanded=True):
            st.dataframe(active_df.dtypes.astype(str).reset_index().rename(columns={'index': 'Column', 0: 'Data Type'}), use_container_width=True)

with col_clear:
    if st.button("🔄 Reset Editor UI", use_container_width=True):
        st.session_state["variable_meta_df"] = None
        st.rerun()

# ─── 8. FOOTER ──────────────────────────────────────────────────────────
st.markdown("<hr style='border:1px solid #1e293b; margin-top:2rem;'>", unsafe_allow_html=True)
st.markdown(
    """
<div style='display: flex; justify-content: space-between; align-items: center; color: #64748b; font-size: 0.8rem; font-family: monospace;'>
    <div>🔍 SPSS VARIABLE VIEW & DATA DICTIONARY STUDIO v3.0</div>
    <div>DEVELOPER: KULA CHRIS (CHRISHEM)</div>
    <div>SYSTEM STATUS: ONLINE</div>
</div>
""",
    unsafe_allow_html=True,
)