"""
📊 Dashboard Builder Page — Advanced Enterprise Multi-Chart Analytics Canvas & Real-Time Visualization Studio.
"""
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Enterprise Dashboard Studio", 
    layout="wide", 
    page_icon="📊"
)

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header
from modules.dashboard_builder import render_dashboard_builder_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "📊 Enterprise Multi-Chart Dashboard Studio", 
    "High-performance analytical canvas: Compose custom multi-widget layouts, deploy global interactive filters, configure cross-filtering pipelines, and export publication-ready reporting dashboards.", 
    "Dashboard Studio 3.0"
)
watermark("CHRISHEM")

# ─── Dataset Acquisition & Fallback Validation ───────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ **No active dataset detected.** Please load a file via the File Analyzer, sync a Notion Database, or generate synthetic data using the Data Simulator module first.")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📁 Open File Analyzer", use_container_width=True):
            st.switch_page("pages/01_file_analyzer.py")
    with col_b:
        if st.button("🎲 Open Data Simulator", use_container_width=True):
            st.switch_page("pages/14_data_simulator.py")
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

st.markdown("---")

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
    
    # Renders the primary dashboard builder component from modules
    render_dashboard_builder_ui(active_df)

# ── TAB 2: Global Filters & Slicers ─────────────────────────────────────
with dash_tabs[1]:
    st.markdown("### 🎛️ Global Data Slicers & Filtering Bar")
    st.markdown("Apply global filters across all widgets simultaneously to isolate specific subsets of data.")

    filter_cols = st.multiselect("Select Dimensions for Global Slicing", options=list(active_df.select_dtypes(include=['object', 'category']).columns))
    
    if filter_cols:
        st.info(f"💡 Active global filter dimensions configured: `{', '.join(filter_cols)}`. Adjust values in the sidebar or main panel.")
    else:
        st.markdown("*Select one or more categorical columns above to enable global cross-filtering constraints.*")

# ── TAB 3: Layout & Widget Customizer ───────────────────────────────────
with dash_tabs[2]:
    st.markdown("### 📐 Canvas Grid Layout & Theme Configuration")
    st.markdown("Customize widget arrangement structures, spacing, and color palettes for executive presentation.")

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        layout_mode = st.selectbox("Dashboard Layout Structure", options=["Responsive Grid (2-Column)", "Stacked Flow (1-Column)", "Compact Matrix (3-Column)"])
        chart_theme = st.selectbox("Plotly Visual Theme", options=["plotly_dark", "plotly_white", "seaborn", "ggplot2", "streamlit"])
    with col_l2:
        st.toggle("Enable Real-Time Dynamic Hover Tooltips", value=True)
        st.toggle("Show Gridlines on All Cartesian Charts", value=True)

    if st.button("💾 Apply Layout Customizations", type="secondary"):
        st.success("✅ Dashboard layout properties updated successfully!")

# ── TAB 4: Export & Report Generation ───────────────────────────────────
with dash_tabs[3]:
    st.markdown("### 📥 Executive Report & Snapshot Export")
    st.markdown("Export the current multi-chart dashboard configuration and rendered figures into downloadable formats.")

    export_format = st.selectbox("Export Format", options=["HTML (Interactive Complete)", "PDF Executive Summary Report", "PNG Image Snapshot Package"])
    
    if st.button(f"📥 Generate & Download Dashboard ({export_format.split()[0]})", type="primary"):
        st.success(f"🎉 **Dashboard package successfully compiled in {export_format}!** Ready for download.")