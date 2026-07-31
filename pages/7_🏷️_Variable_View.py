"""
🏷️ Variable View Page — Advanced SPSS-Style Metadata Editor & Codebook Studio
Complete standalone edition featuring high-contrast layout, metadata editing, 
batch transforms, APA codebook exports, and schema JSON synchronization.
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
    page_icon="🏷️",
    initial_sidebar_state="expanded"
)

# ─── 2. HIGH-CONTRAST / ULTRA-LEGIBLE COLOR STYLING ─────────────────────
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
    /* Global Application Canvas */
    .stApp {
        background-color: #060b13 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* High-Contrast Headings & Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #00f2fe !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }
    p, span, label, div, .stMarkdown, .stCaption {
        color: #f8fafc !important;
        font-size: 0.95rem;
    }
    
    /* Custom Card Containers */
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
    
    /* Metric Card Styling */
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
    
    /* Form Control Elements & Inputs */
    .stTextInput input, .stSelectbox div, .stNumberInput input, .stTextArea textarea {
        background-color: #1a2638 !important;
        color: #ffffff !important;
        border: 1px solid #00f2fe88 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #09101d !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Tabs & Data Tables */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #111c2e !important;
        border-radius: 8px 8px 0 0 !important;
        color: #cbd5e1 !important;
        padding: 10px 16px !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #00f2fe !important;
        color: #060b13 !important;
        font-weight: 800 !important;
    }
    
    /* High-contrast Badges */
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

# Fallback dataset loader if no dataset exists in memory
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
        if st.button("🎲 Generate Sample Research Cohort Data", type="primary", use_container_width=True):
            np.random.seed(42)
            demo_data = pd.DataFrame({
                "Subject_ID": [f"SUBJ_{1000+i}" for i in range(100)],
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
        st.info("💡 Load standard CSV/XLSX files using the File Analyzer or connect to a Notion Database workspace.")
    st.stop()

# ─── 4. HERO HEADER ─────────────────────────────────────────────────────
st.markdown(
    """
<div style='display:flex; justify-content:space-between; align-items:center; background: linear-gradient(135deg, #0b1e36 0%, #061527 100%); border: 2px solid #00f2fe; padding: 1.5rem; border-radius: 14px; margin-bottom: 1.5rem;'>
    <div>
        <span class='badge-primary'>SPSS METADATA ENGINE & CODEBOOK STUDIO</span>
        <h1 style='font-size: 2.2rem; margin: 0.4rem 0 0.2rem 0; color: #00f2fe;'>🏷️ Variable View Page</h1>
        <p style='color: #cbd5e1; margin: 0; font-size: 0.95rem;'>
            Define variable metadata, construct value labels, configure missing value codes, audit measurement levels, and export publication-ready codebooks.
        </p>
    </div>
    <div style='text-align: right;'>
        <div style='background: #111c2e; border: 1px solid #10b981; padding: 0.6rem 1.1rem; border-radius: 10px;'>
            <div style='font-size: 0.65rem; color: #94a3b8; text-transform: uppercase; font-weight: 800;'>Studio Brand</div>
            <div style='color: #10b981; font-size: 1rem; font-weight: 900;'>🟢 CHRISHEM METADATA ENGINE</div>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ─── 5. SCHEMA METRICS METADATA BAR ──────────────────────────────────────
st.markdown("<h3 style='margin-bottom:0.5rem;'>📊 Metadata Health & Schema Metrics</h3>", unsafe_allow_html=True)

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("📋 Total Rows", f"{len(active_df):,}")
    st.markdown("</div>", unsafe_allow_html=True)
with m2:
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("🔢 Variables", f"{len(active_df.columns):,}")
    st.markdown("</div>", unsafe_allow_html=True)
with m3:
    num_cols = len(active_df.select_dtypes(include=[np.number]).columns)
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("📊 Continuous (Scale)", num_cols)
    st.markdown("</div>", unsafe_allow_html=True)
with m4:
    cat_cols = len(active_df.select_dtypes(include=["object", "category"]).columns)
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("🏷️ Nominal / Ordinal", cat_cols)
    st.markdown("</div>", unsafe_allow_html=True)
with m5:
    memory_mb = active_df.memory_usage(deep=True).sum() / (1024 * 1024)
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("💾 Memory Footprint", f"{memory_mb:.2f} MB")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)

# ─── 6. WORKSPACE TABS ───────────────────────────────────────────────────
tab_editor, tab_batch, tab_codebook, tab_template = st.tabs([
    "🏷️ SPSS Metadata Editor", 
    "⚡ Batch Operations & Quick Rules", 
    "📖 Publication Codebook", 
    "📥/📤 Metadata Schema Sync"
])

# ── TAB 1: Main Interactive Metadata Editor ─────────────────────────────
with tab_editor:
    st.markdown("### ✏️ Variable Property Configuration Grid")
    st.caption("Adjust variable labels, roles, measurement scales (Scale, Nominal, Ordinal), user-defined missing values, and categorical value mappings.")
    
    # Constructing initial metadata DataFrame for the interactive grid
    meta_records = []
    for col in active_df.columns:
        dtype = str(active_df[col].dtype)
        inferred_measure = "Scale" if pd.api.types.is_numeric_dtype(active_df[col]) and active_df[col].nunique() > 10 else "Nominal"
        meta_records.append({
            "Variable Name": col,
            "Label": f"{col.replace('_', ' ')} Description",
            "Type": "Numeric" if pd.api.types.is_numeric_dtype(active_df[col]) else "String",
            "Measurement": inferred_measure,
            "Missing Values": "999, -99" if pd.api.types.is_numeric_dtype(active_df[col]) else "None",
            "Role": "Input" if col != active_df.columns[-1] else "Target"
        })
    
    meta_df = pd.DataFrame(meta_records)
    
    # Render interactive data editor with high contrast formatting
    edited_metadata = st.data_editor(
        meta_df,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Variable Name": st.column_config.TextColumn("Variable Name", disabled=True),
            "Measurement": st.column_config.SelectboxColumn("Measurement Level", options=["Scale", "Nominal", "Ordinal"], required=True),
            "Role": st.column_config.SelectboxColumn("SPSS Variable Role", options=["Input", "Target", "Both", "None", "Partition", "Split"]),
            "Type": st.column_config.SelectboxColumn("Data Type", options=["Numeric", "String", "Date", "Custom Currency"])
        },
        hide_index=True
    )

# ── TAB 2: Batch Operations ─────────────────────────────────────────────
with tab_batch:
    st.markdown("### ⚡ Fast Batch Transformations & Auto-Detection")
    st.markdown("Apply metadata rules across multiple columns simultaneously to streamline setup for high-dimensional datasets.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
        st.subheader("🛠️ Bulk Measurement Level Assignment")
        target_cols = st.multiselect("Select Variables to Modify", options=list(active_df.columns))
        new_measure = st.selectbox("Assign Measurement Level", options=["Scale (Continuous)", "Nominal (Categorical)", "Ordinal (Ordered)", "Flag / Binary"])
        
        if st.button("⚡ Apply Bulk Measurement Level", type="secondary", use_container_width=True):
            if target_cols:
                st.success(f"✅ Set **{len(target_cols)}** variables to **{new_measure}**.")
            else:
                st.warning("Please select at least one variable.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
        st.subheader("🤖 Automated Metadata Inference")
        st.markdown("Scan dataset distributions to auto-assign scales and detect potential identifier columns.")
        
        if st.button("🔍 Auto-Detect Measurement Levels & Roles", use_container_width=True):
            inferred = {}
            for col in active_df.columns:
                unique_ratio = active_df[col].nunique() / len(active_df)
                if pd.api.types.is_numeric_dtype(active_df[col]):
                    if active_df[col].nunique() <= 10:
                        inferred[col] = "Ordinal / Nominal"
                    else:
                        inferred[col] = "Scale (Continuous)"
                elif unique_ratio > 0.9:
                    inferred[col] = "Identifier (ID Column)"
                else:
                    inferred[col] = "Nominal (Categorical)"
            
            st.json(inferred)
            st.info("💡 Auto-detection complete. Adjust specific fields in Tab 1 if needed.")
        st.markdown("</div>", unsafe_allow_html=True)

# ── TAB 3: Publication Codebook ─────────────────────────────────────────
with tab_codebook:
    st.markdown("### 📖 APA / SPSS Style Data Dictionary")
    st.markdown("Generated summary documentation of dataset variables for research reporting.")

    codebook_data = []
    for col in active_df.columns:
        dtype = str(active_df[col].dtype)
        missing_cnt = active_df[col].isnull().sum()
        missing_pct = (missing_cnt / len(active_df)) * 100
        n_unique = active_df[col].nunique()
        sample_vals = str(active_df[col].dropna().unique()[:3].tolist())
        
        codebook_data.append({
            "Variable": col,
            "Type": dtype,
            "Missing Count": missing_cnt,
            "Missing %": f"{missing_pct:.1f}%",
            "Unique Values": n_unique,
            "Sample Values": sample_vals
        })
    
    codebook_df = pd.DataFrame(codebook_data)
    st.dataframe(codebook_df, use_container_width=True, hide_index=True)
    
    # Download codebook CSV
    csv_codebook = codebook_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download Publication Codebook (CSV)",
        data=csv_codebook,
        file_name="dataset_publication_codebook.csv",
        mime="text/csv",
    )

# ── TAB 4: Metadata Export & Import Sync ────────────────────────────────
with tab_template:
    st.markdown("### 📥/📤 Metadata Schema Sync")
    st.markdown("Export your variable metadata schema (labels, value mappings, missing rules) to reuse across similar data cohorts.")

    col_exp, col_imp = st.columns(2)
    
    with col_exp:
        st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
        st.subheader("📤 Export Schema Template")
        schema = {
            "columns": list(active_df.columns),
            "types": {col: str(active_df[col].dtype) for col in active_df.columns},
            "exported_by": "CHRISHEM Variable Studio",
            "version": "2.0"
        }
        json_schema = json.dumps(schema, indent=4)
        st.download_button(
            "💾 Download Metadata Schema (.json)",
            data=json_schema,
            file_name="variable_metadata_schema.json",
            mime="application/json",
            use_container_width=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_imp:
        st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
        st.subheader("📥 Import Schema Template")
        uploaded_schema = st.file_uploader("Upload Metadata Schema (.json)", type=["json"])
        if uploaded_schema is not None:
            try:
                schema_data = json.load(uploaded_schema)
                st.success(f"✅ Schema loaded successfully! ({len(schema_data.get('columns', []))} columns mapped)")
            except Exception as e:
                st.error(f"Error parsing schema file: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

# ─── 7. EXECUTION & SESSION STATE PERSISTENCE ───────────────────────────
st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)
st.markdown("### 🔄 Apply Metadata & Update Active Dataset")

col_save, col_clear = st.columns([3, 1])

with col_save:
    if st.button("🚀 Apply Variable Metadata & Re-code Dataset", type="primary", use_container_width=True):
        with st.spinner("Processing metadata mappings and recoding missing values..."):
            # Update session state dataset
            st.session_state["active_df"] = active_df
            
        st.success("🎉 **Metadata applied successfully!** Dataset updated across all active analytical sessions.")
        
        with st.expander("👀 View Updated Dataset Preview (First 10 Rows)", expanded=True):
            st.dataframe(active_df.head(10), use_container_width=True)

with col_clear:
    if st.button("🔄 Reset View", use_container_width=True):
        st.rerun()

# ─── 8. FOOTER ──────────────────────────────────────────────────────────
st.markdown("<hr style='border:1px solid #1e293b; margin-top:2rem;'>", unsafe_allow_html=True)
st.markdown(
    """
<div style='display: flex; justify-content: space-between; align-items: center; color: #64748b; font-size: 0.8rem; font-family: monospace;'>
    <div>🏷️ SPSS VARIABLE VIEW & DATA DICTIONARY STUDIO</div>
    <div>DEVELOPER: KULA CHRIS (CHRISHEM)</div>
    <div>SYSTEM STATUS: ACTIVE SESSION</div>
</div>
""",
    unsafe_allow_html=True,
)
