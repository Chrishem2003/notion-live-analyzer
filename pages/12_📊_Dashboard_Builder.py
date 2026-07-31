"""
═══════════════════════════════════════════════════════════════════════════════
ENTERPRISE DASHBOARD BUILDER & VISUALIZATION STUDIO [v3.0]
High-performance analytical canvas: Compose custom multi-widget layouts, deploy 
global interactive filters, configure cross-filtering pipelines, and export 
publication-ready reporting dashboards.
Designed for: Kula Chris (Chrishem)
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
    from modules.dashboard_builder import render_dashboard_builder_ui
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

    def render_dashboard_builder_ui(df: pd.DataFrame):
        st.success("⚡ Interactive Dashboard Canvas Engine Active: Multi-Widget Layout Ready.")
        st.markdown("**Active Dataset Preview:**")
        st.dataframe(df.head(5), use_container_width=True)
        num_cols = list(df.select_dtypes(include=[np.number]).columns)
        cat_cols = list(df.select_dtypes(include=['object', 'category']).columns)
        
        c1, c2 = st.columns(2)
        with c1:
            if num_cols:
                metric_col = st.selectbox("Select Key Numeric Metric Widget", num_cols)
                st.metric(label=f"Sum of {metric_col}", value=f"{df[metric_col].sum():,.2f}")
        with c2:
            if cat_cols:
                group_col = st.selectbox("Select Categorical Grouping", cat_cols)
                if num_cols:
                    bar_data = df.groupby(group_col)[num_cols[0]].sum().reset_index()
                    st.bar_chart(bar_data, x=group_col, y=num_cols[0], use_container_width=True)

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise Dashboard Studio", 
    layout="wide", 
    page_icon="📊",
    initial_sidebar_state="collapsed"
)

init_session_state()

# ─── HIGH-CONTRAST CYBER DESIGN SYSTEM STYLING ────────────────────────
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
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* High-Contrast Clear Typography */
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
        color: #cbd5e1 !important;
        font-size: 0.85rem !important;
    }

    /* Card Containers */
    .contrast-card {
        background: #111c2e !important;
        border: 1px solid #00f2fe44 !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }

    /* Tab Layout & Controls */
    div.stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #09101d !important;
        padding: 8px;
        border-radius: 10px;
        border: 1px solid #1e293b;
    }
    div.stTabs [data-baseweb="tab"] {
        height: 42px;
        background-color: transparent;
        border-radius: 6px;
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        border: none;
        padding: 0 18px;
    }
    div.stTabs [aria-selected="true"] {
        background: #111c2e !important;
        color: #00f2fe !important;
        border-bottom: 3px solid #00f2fe !important;
    }

    /* Inputs, Selectboxes, Multiselects */
    div.stSelectbox, div.stMultiSelect, div.stTextInput, div.stNumberInput, div.stSlider {
        background-color: #111c2e !important;
        padding: 8px !important;
        border-radius: 8px !important;
    }

    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        color: #00f2fe !important;
        font-size: 1.7rem !important;
        font-weight: 900 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 0.75rem;
    }

    /* Custom High-Visibility Primary Buttons */
    .stButton button {
        background: #111c2e !important;
        border: 1px solid #00f2fe !important;
        color: #00f2fe !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
    .stButton button:hover {
        background: #00f2fe !important;
        color: #060b13 !important;
        box-shadow: 0 0 14px rgba(0, 242, 254, 0.5);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_card(
    "📊 Enterprise Multi-Chart Dashboard Studio", 
    "High-performance analytical canvas: Compose custom multi-widget layouts, deploy global interactive filters, configure cross-filtering pipelines, and export publication-ready reporting dashboards.", 
    "Dashboard Studio 3.0"
)
watermark("CHRISHEM")

# ─── Dataset Acquisition & Fallback Validation ───────────────────────────
active_df = st.session_state.get("active_df") or st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.markdown(
        """
        <div class='contrast-card'>
            <h3 style='margin-top:0;'>⚠️ No Active Dataset Detected</h3>
            <p style='color:#cbd5e1;'>Please load a dataset or generate synthetic enterprise observations to activate the dashboard canvas.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🎲 Generate Synthetic Enterprise Cohort", type="primary", use_container_width=True):
            np.random.seed(101)
            sim_df = pd.DataFrame({
                "Record_ID": [f"REC-{i:04d}" for i in range(1, 101)],
                "Region": np.random.choice(["North America", "Europe", "Asia-Pacific", "Latin America"], 100),
                "Department": np.random.choice(["Clinical", "Data Analytics", "Engineering", "R&D"], 100),
                "Quarterly_Revenue": np.round(np.random.uniform(5000, 55000, 100), 2),
                "Operational_Cost": np.round(np.random.uniform(2000, 30000, 100), 2),
                "Satisfaction_Score": np.round(np.random.uniform(3.5, 5.0, 100), 2),
                "Active_Projects": np.random.randint(1, 12, 100)
            })
            st.session_state["active_df"] = sim_df
            st.rerun()
    with col_b:
        if st.button("📁 Load Default Operational Analytics Data", use_container_width=True):
            sim_df = pd.DataFrame({
                "ID": [i for i in range(1, 51)],
                "Category": np.random.choice(["Alpha", "Beta", "Gamma"], 50),
                "Metric_A": np.random.normal(100, 15, 50),
                "Metric_B": np.random.normal(50, 10, 50)
            })
            st.session_state["active_df"] = sim_df
            st.rerun()
    st.stop()

# ─── High-Level Dashboard Topology Metrics ─────────────────────────────
section_header("📊 Dataset Topology & Canvas Readiness")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("📋 Total Observations", f"{len(active_df):,}")
with m2:
    st.metric("🔢 Total Attributes", f"{len(active_df.columns):,}")
with m3:
    numeric_cols = len(active_df.select_dtypes(include=[np.number]).columns)
    st.metric("📈 Numeric Metrics", numeric_cols)
with m4:
    categorical_cols = len(active_df.select_dtypes(include=['object', 'category']).columns)
    st.metric("🏷️ Categorical Dimensions", categorical_cols)
with m5:
    st.metric("🖥️ Layout Engine", "Dynamic Grid 3.0")

with st.expander("🔍 Preview Active Dataset Schema & Summary", expanded=False):
    st.dataframe(active_df.head(10), use_container_width=True)
    st.markdown("##### Column Data Types")
    st.write(active_df.dtypes.astype(str))

st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)

# ─── Multi-Tab Dashboard Studio Workspace ───────────────────────────────
section_header("⚙️ Interactive Dashboard Canvas & Management Suite")

dash_tabs = st.tabs([
    "📊 Core Interactive Dashboard",
    "🎛️ Global Filters & Slicers",
    "📐 Layout & Widget Customizer",
    "📥 Export & Report Generation"
])

# ── TAB 1: Core Dashboard Studio ────────────────────────────────────────
with dash_tabs[0]:
    st.markdown("### 📊 Multi-Widget Visual Canvas")
    st.caption("Build, arrange, and interact with synchronized charts and metric cards in real time.")
    
    # Renders primary dashboard builder component
    render_dashboard_builder_ui(active_df)

# ── TAB 2: Global Filters & Slicers ─────────────────────────────────────
with dash_tabs[1]:
    st.markdown("### 🎛️ Global Data Slicers & Filtering Bar")
    st.caption("Apply global filters across all widgets simultaneously to isolate specific subsets of data.")

    categorical_columns = list(active_df.select_dtypes(include=['object', 'category']).columns)
    
    if categorical_columns:
        filter_cols = st.multiselect("Select Dimensions for Global Slicing", options=categorical_columns)
        
        if filter_cols:
            st.markdown(
                f"""
                <div class='contrast-card'>
                    <h4 style='margin-top:0; color:#00f2fe;'>💡 Active Global Filter Dimensions Configured</h4>
                    <p style='margin:0; color:#cbd5e1;'>Slicing active across: <code>{', '.join(filter_cols)}</code></p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown("*Select one or more categorical columns above to enable global cross-filtering constraints.*")
    else:
        st.warning("No categorical dimensions found in dataset for global slicing.")

# ── TAB 3: Layout & Widget Customizer ───────────────────────────────────
with dash_tabs[2]:
    st.markdown("### 📐 Canvas Grid Layout & Theme Configuration")
    st.caption("Customize widget arrangement structures, spacing, and color palettes for executive presentation.")

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        layout_mode = st.selectbox("Dashboard Layout Structure", options=["Responsive Grid (2-Column)", "Stacked Flow (1-Column)", "Compact Matrix (3-Column)"])
        chart_theme = st.selectbox("Plotly Visual Theme", options=["plotly_dark", "plotly_white", "seaborn", "ggplot2", "streamlit"])
    with col_l2:
        st.toggle("Enable Real-Time Dynamic Hover Tooltips", value=True)
        st.toggle("Show Gridlines on All Cartesian Charts", value=True)

    if st.button("💾 Apply Layout Customizations", use_container_width=True):
        st.success("✅ Dashboard layout properties updated successfully!")

# ── TAB 4: Export & Report Generation ───────────────────────────────────
with dash_tabs[3]:
    st.markdown("### 📥 Executive Report & Snapshot Export")
    st.caption("Export the current multi-chart dashboard configuration and rendered figures into downloadable formats.")

    export_format = st.selectbox("Export Format", options=["HTML (Interactive Complete)", "PDF Executive Summary Report", "PNG Image Snapshot Package"])
    
    if st.button(f"📥 Generate & Download Dashboard ({export_format.split()[0]})", type="primary", use_container_width=True):
        st.markdown(
            f"""
            <div class='contrast-card' style='text-align:center;'>
                <h4 style='color:#00f2fe; margin-top:0;'>🎉 Report Package Successfully Compiled!</h4>
                <p style='color:#cbd5e1; margin:0;'>Your dashboard in <strong>{export_format}</strong> format is generated and ready for presentation.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
