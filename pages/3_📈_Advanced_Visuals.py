"""
📈 World-Class Advanced Visuals Engine — 18+ Interactive Charts, Automated Recommendations,
Advanced Filtering, Statistical Overlays, Custom Layout Configuration, and High-Resolution Export.
"""
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Advanced Visuals Studio [SECURE]", layout="wide", page_icon="📈")
import sys
import os
from pathlib import Path

# ─── ULTIMATE PATH RESOLUTION ────────────────────────────────────────
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(current_file.parent) not in sys.path:
    sys.path.insert(0, str(current_file.parent))

from modules.config import init_session_state, CHART_COLOR_PALETTES
from modules.ui_components import hero_card, section_header, load_css, watermark
from modules.chart_builder import build_chart
from modules.viz_engine import ALL_CHART_TYPES, auto_recommend_chart, get_chart_search_results, explain_chart_recommendation
from modules.data_processor import infer_column_types
from modules.export import get_chart_download_link, render_export_buttons

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "📈 World-Class Advanced Visualization Studio [CLASSIFIED]",
    "18+ interactive chart types with CHRISHEM-powered auto-recommendation, live dataset filtering, "
    "statistical aggregation, custom templates, and publication-ready exports.",
    badge_text="🔒 v5.0 — Enterprise Chart Studio & Analytics Engine"
)
watermark("CHRISHEM")

# ─── Data Selection & Validation ──────────────────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ No active dataset available. Please load data from the File Analyzer or Notion workspace first.")
    st.stop()

# Get column metadata & categorized lists
col_types = infer_column_types(active_df)
all_columns = active_df.columns.tolist()
numeric_cols = [c for c in all_columns if col_types.get(c) in ("numeric", "integer")]
cat_cols = [c for c in all_columns if col_types.get(c) in ("categorical", "string")]
temporal_cols = [c for c in all_columns if col_types.get(c) == "temporal"]

# ─── Global Sidebar / Expandable Dataset Filter & Transformation ──────
with st.expander("🛠️ Optional: Dataset Row Filtering & Slice Controls", expanded=False):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_col = st.selectbox("Filter Column (Optional)", options=[""] + all_columns, key="viz_filter_col")
    with col_f2:
        if filter_col and filter_col in cat_cols:
            unique_vals = active_df[filter_col].dropna().unique().tolist()
            selected_vals = st.multiselect(f"Keep values in {filter_col}", options=unique_vals, default=unique_vals[:min(10, len(unique_vals))])
            if selected_vals:
                active_df = active_df[active_df[filter_col].isin(selected_vals)]
        elif filter_col and filter_col in numeric_cols:
            min_v, max_v = float(active_df[filter_col].min()), float(active_df[filter_col].max())
            val_range = st.slider(f"Range for {filter_col}", min_value=min_v, max_value=max_v, value=(min_v, max_v))
            active_df = active_df[(active_df[filter_col] >= val_range[0]) & (active_df[filter_col] <= val_range[1])]

# ─── Main Navigation Tabs ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🤖 Auto-Recommend AI", 
    "🎨 Pro Custom Builder", 
    "🔍 Semantic Chart Search",
    "📊 Multi-Chart Dashboard"
])

# ───────────────────────────────────────────────────────────────────────
# TAB 1: AUTO-RECOMMEND ENGINE
# ───────────────────────────────────────────────────────────────────────
with tab1:
    section_header("🤖 CHRISHEM-Powered Automated Chart Studio")
    st.caption("Select columns below to let the automated recommendation engine compute and render the highest-impact visual configurations.")

    col_sel1, col_sel2 = st.columns([3, 1])
    with col_sel1:
        selected_cols = st.multiselect(
            "Select Target Columns to Analyze",
            options=all_columns,
            default=numeric_cols[:2] + cat_cols[:1] if numeric_cols else all_columns[:3],
            key="auto_rec_multiselect",
            help="Engine evaluates distribution, correlation, and cardinality across columns."
        )
    with col_sel2:
        max_recs = st.number_input("Max Recommendations", min_value=1, max_value=12, value=6, step=1)

    if selected_cols:
        recommendations = auto_recommend_chart(active_df, selected_cols)

        if recommendations:
            st.markdown(f"**Successfully generated {min(len(recommendations), max_recs)} tailored visualization option(s)**")
            for i, rec in enumerate(recommendations[:max_recs]):
                with st.container():
                    st.markdown(f"---")
                    col_exp, col_chart = st.columns([1, 2])
                    
                    with col_exp:
                        st.markdown(explain_chart_recommendation(rec))
                        chart_type = rec["chart"]
                        st.caption(f"📌 Architecture: {chart_type.replace('_', ' ').title()}")
                        
                        # Quick render trigger for individual recommendation export
                        chart_kwargs = {k: rec[k] for k in ("x", "y", "color", "size", "z", "path", "values", "dimensions") if rec.get(k) is not None}
                        rec_fig = build_chart(chart_type, active_df, **chart_kwargs, height=320)
                        if rec_fig:
                            dl_link = get_chart_download_link(rec_fig, f"recommended_{chart_type}_{i}", "png")
                            if dl_link:
                                st.markdown(dl_link, unsafe_allow_html=True)

                    with col_chart:
                        if rec_fig:
                            st.plotly_chart(rec_fig, use_container_width=True)
                        else:
                            st.info(f"⚠️ Could not build {chart_type} with the selected column parameters.")
        else:
            st.info("📭 No recommendations available for this exact column combination. Try selecting a mix of numeric and categorical variables.")
    else:
        st.info("👈 Please select at least one column above to trigger automated chart recommendations.")

# ───────────────────────────────────────────────────────────────────────
# TAB 2: PRO CUSTOM CHART BUILDER
# ───────────────────────────────────────────────────────────────────────
with tab2:
    section_header("🎨 Enterprise Custom Chart Builder")
    st.caption("Full parameter control over chart geometry, mapping axes, color palettes, and dimensions.")

    col1, col2, col3 = st.columns(3)

    with col1:
        chart_type = st.selectbox(
            "Chart Architecture Type",
            options=ALL_CHART_TYPES,
            index=0,
            format_func=lambda x: x.replace("_", " ").title(),
            key="custom_chart_type_select"
        )
        x_col = st.selectbox("X-Axis / Category Column", options=[""] + all_columns, index=0, key="custom_x")

    with col2:
        y_col = st.selectbox("Y-Axis / Metric Column", options=[""] + all_columns, index=0, key="custom_y")
        color_col = st.selectbox("Color Grouping Variable", options=[""] + all_columns, index=0, key="custom_color")

    with col3:
        size_col = st.selectbox("Bubble Size Variable (Numeric)", options=[""] + numeric_cols, index=0, key="custom_size")
        z_col = st.selectbox("Z-Axis Variable (3D Plots)", options=[""] + numeric_cols, index=0, key="custom_z")

    # Advanced styling parameters
    with st.expander("⚙️ Advanced Styling & Layout Configuration", expanded=False):
        col_st1, col_st2, col_st3 = st.columns(3)
        with col_st1:
            palette = st.selectbox("Color Palette Scheme", options=list(CHART_COLOR_PALETTES.keys()), index=0, key="custom_palette")
        with col_st2:
            height = st.slider("Chart Canvas Height (px)", min_value=350, max_value=850, value=500, step=25, key="custom_height")
        with col_st3:
            trendline_option = st.selectbox("Statistical Trendline (Scatter)", options=["None", "ols", "lowess"], index=0, key="custom_trendline")

    # Assemble kwargs
    chart_kwargs = {}
    if x_col:
        chart_kwargs["x"] = x_col
    if y_col:
        chart_kwargs["y"] = y_col
    if color_col:
        chart_kwargs["color"] = color_col
    if size_col and chart_type in ("bubble", "scatter"):
        chart_kwargs["size"] = size_col
    if z_col and chart_type in ("scatter_3d",):
        chart_kwargs["z"] = z_col
    if trendline_option != "None" and chart_type == "scatter":
        chart_kwargs["trendline"] = trendline_option

    chart_kwargs["palette"] = palette
    chart_kwargs["height"] = height

    if st.button("🚀 Render Custom Chart Studio Output", type="primary", use_container_width=True):
        if not x_col and not y_col:
            st.warning("⚠️ Please select at least an X-axis or Y-axis column to build the visualization.")
        else:
            with st.spinner("Rendering high-performance interactive plot..."):
                fig = build_chart(chart_type, active_df, **chart_kwargs)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("---")
                    section_header("📥 Export High-Resolution Visual")
                    col_ex1, col_ex2 = st.columns(2)
                    with col_ex1:
                        png_link = get_chart_download_link(fig, f"custom_{chart_type}", "png")
                        if png_link:
                            st.markdown(png_link, unsafe_allow_html=True)
                    with col_ex2:
                        html_link = get_chart_download_link(fig, f"custom_{chart_type}", "html")
                        if html_link:
                            st.markdown(html_link, unsafe_allow_html=True)
                else:
                    st.error(f"❌ Failed to construct '{chart_type}' chart with the selected parameters. Check column data types.")

# ───────────────────────────────────────────────────────────────────────
# TAB 3: SEMANTIC CHART SEARCH
# ───────────────────────────────────────────────────────────────────────
with tab3:
    section_header("🔍 Semantic Chart Search by Analytical Purpose")
    st.caption("Describe your analytical objective (e.g., 'distribution', 'time-series trend', 'correlation', 'hierarchy'), and the engine will map the optimal chart type.")

    search_query = st.text_input("Enter analytical objective or keyword", placeholder="e.g., compare categories, show composition, trace timeline trend", key="chart_search_input")
    
    if search_query:
        results = get_chart_search_results(search_query)
        if results:
            st.markdown(f"**Found {len(results)} matching chart architecture(s)**")
            for chart_type, desc in results:
                with st.container():
                    st.markdown(f"### 📈 {chart_type.replace('_', ' ').title()}")
                    st.caption(desc)
                    
                    # Auto-build preview using best available columns
                    recs = auto_recommend_chart(active_df)
                    matching_recs = [r for r in recs if r["chart"] == chart_type]
                    if matching_recs:
                        rec = matching_recs[0]
                        sub_kwargs = {k: rec[k] for k in ("x", "y", "color", "size", "z", "path", "values", "dimensions") if rec.get(k) is not None}
                        fig_prev = build_chart(chart_type, active_df, **sub_kwargs, height=350)
                        if fig_prev:
                            st.plotly_chart(fig_prev, use_container_width=True)
                    else:
                        st.info(f"ℹ️ Quick preview not available for {chart_type} with current dataset schema.")
                    st.markdown("---")
        else:
            st.warning(f"⚠️ No matching chart type found for '{search_query}'. Try keywords like: trend, distribution, comparison, correlation.")

    # Quick Select Grid
    st.markdown("### 📌 Quick-Access Standard Visualizations")
    quick_charts = {
        "📊 Distribution": "histogram",
        "📈 Trend Over Time": "line",
        "🔗 Category Comparison": "bar",
        "🔵 Scatter Correlation": "scatter",
        "🥧 Proportional Composition": "pie",
        "📦 Statistical Box Plot": "box",
        "🎯 Multi-Dimension Matrix": "parallel_coordinates",
        "🏠 Hierarchical Treemap": "treemap",
    }
    
    q_cols = st.columns(4)
    for i, (label, chart_type) in enumerate(quick_charts.items()):
        with q_cols[i % 4]:
            if st.button(label, use_container_width=True, key=f"quick_btn_{chart_type}"):
                recs = auto_recommend_chart(active_df)
                matching = [r for r in recs if r["chart"] == chart_type]
                if matching:
                    rec = matching[0]
                    q_kwargs = {k: rec[k] for k in ("x", "y", "color", "size", "z", "path", "values", "dimensions") if rec.get(k) is not None}
                    q_fig = build_chart(chart_type, active_df, **q_kwargs, height=450)
                    if q_fig:
                        st.plotly_chart(q_fig, use_container_width=True)
                else:
                    st.info(f"⚠️ Unable to generate {chart_type} automatically with current data types.")

# ───────────────────────────────────────────────────────────────────────
# TAB 4: MULTI-CHART DASHBOARD VIEW
# ───────────────────────────────────────────────────────────────────────
with tab4:
    section_header("📊 Multi-Chart Executive Dashboard")
    st.markdown("Simultaneous side-by-side rendering of key dataset metrics and distributions.")

    if len(numeric_cols) >= 2:
        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            st.markdown(f"**Primary Metric Distribution: {numeric_cols[0]}**")
            fig_d1 = build_chart("histogram", active_df, x=numeric_cols[0], height=350)
            if fig_d1:
                st.plotly_chart(fig_d1, use_container_width=True)
                
        with col_d2:
            st.markdown(f"**Secondary Correlation: {numeric_cols[0]} vs {numeric_cols[1]}**")
            fig_d2 = build_chart("scatter", active_df, x=numeric_cols[0], y=numeric_cols[1], height=350)
            if fig_d2:
                st.plotly_chart(fig_d2, use_container_width=True)
    else:
        st.info("ℹ️ Multi-chart executive dashboard requires at least 2 numeric columns in the dataset.")