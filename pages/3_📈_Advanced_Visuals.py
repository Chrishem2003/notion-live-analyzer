"""
📈 Advanced Visuals Page — 18+ chart types with auto-recommendation and full customization.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Advanced Visuals", layout="wide", page_icon="📈")

from modules.config import init_session_state, CHART_COLOR_PALETTES
from modules.ui_components import hero_card, section_header, load_css, watermark
from modules.chart_builder import build_chart
from modules.viz_engine import ALL_CHART_TYPES, auto_recommend_chart, get_chart_search_results, explain_chart_recommendation
from modules.data_processor import infer_column_types

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("📈 Advanced Visualization Engine", "18+ interactive chart types with CHRISHEM-powered auto-recommendation.", "Chart Studio")
watermark("CHRISHEM")

# ─── Data Selection ──────────────────────────────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ No data available. Load data from Notion or upload a file first.")
    st.stop()

# Get column info
col_types = infer_column_types(active_df)
all_columns = active_df.columns.tolist()
numeric_cols = [c for c in all_columns if col_types.get(c) in ("numeric", "integer")]
cat_cols = [c for c in all_columns if col_types.get(c) in ("categorical", "string")]
temporal_cols = [c for c in all_columns if col_types.get(c) == "temporal"]

# ─── Mode Selection ──────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🤖 Auto-Recommend", "🎨 Custom Chart Builder", "🔍 Search Charts"])

# ─── TAB 1: Auto-Recommend ──────────────────────────────────────────
with tab1:
    section_header("🤖 CHRISHEM-Powered Chart Recommendations")
    st.caption("Select columns and let CHRISHEM recommend the best visualization")


    selected_cols = st.multiselect(
        "Select columns to visualize",
        options=all_columns,
        default=numeric_cols[:2] + cat_cols[:1] if numeric_cols else all_columns[:3],
        help="CHRISHEM will analyze the selected columns and recommend the best chart types"
    )

    if selected_cols:
        recommendations = auto_recommend_chart(active_df, selected_cols)

        if recommendations:
            st.markdown(f"**Recommended {len(recommendations)} chart options**")
            for i, rec in enumerate(recommendations[:8]):
                with st.container():
                    col_exp, col_chart = st.columns([1, 2])
                    with col_exp:
                        st.markdown(explain_chart_recommendation(rec))
                        chart_type = rec["chart"]
                        st.caption(f"Type: {chart_type.replace('_', ' ').title()}")
                    with col_chart:
                        chart_kwargs = {k: rec[k] for k in ("x", "y", "color", "size", "z", "path", "values", "dimensions") if rec.get(k) is not None}
                        chart = build_chart(chart_type, active_df, **chart_kwargs, height=350)
                        if chart:
                            st.plotly_chart(chart, use_container_width=True)
                        else:
                            st.info(f"Could not build {chart_type} with selected columns")
                    st.markdown("---")
        else:
            st.info("No recommendations available for the selected columns. Try different column combinations.")
    else:
        st.info("Select at least one column to get chart recommendations.")

# ─── TAB 2: Custom Chart Builder ────────────────────────────────────
with tab2:
    section_header("🎨 Custom Chart Builder")
    st.caption("Manually configure every aspect of your visualization")

    col1, col2 = st.columns([1, 1])

    with col1:
        chart_type = st.selectbox(
            "Chart type",
            options=ALL_CHART_TYPES,
            index=0,
            format_func=lambda x: x.replace("_", " ").title(),
        )

        x_col = st.selectbox("X-axis", options=[""] + all_columns, index=0)
        y_col = st.selectbox("Y-axis", options=[""] + all_columns, index=0)
        color_col = st.selectbox("Color by", options=[""] + all_columns, index=0)

    with col2:
        size_col = st.selectbox("Size (for bubble)", options=[""] + numeric_cols, index=0)
        z_col = st.selectbox("Z-axis (for 3D)", options=[""] + numeric_cols, index=0)
        palette = st.selectbox("Color palette", options=list(CHART_COLOR_PALETTES.keys()), index=0)
        height = st.slider("Chart height", 300, 700, 430, 10)

    # Build chart
    chart_kwargs = {}
    if x_col:
        chart_kwargs["x"] = x_col
    if y_col:
        chart_kwargs["y"] = y_col
    if color_col:
        chart_kwargs["color"] = color_col
    if size_col and chart_type == "bubble":
        chart_kwargs["size"] = size_col

    if chart_type in ("scatter_3d",) and z_col:
        chart_kwargs["z"] = z_col

    chart_kwargs["palette"] = palette
    chart_kwargs["height"] = height

    if st.button("🎯 Generate Chart", type="primary"):
        if not x_col and not y_col:
            st.warning("Please select at least an X-axis or Y-axis column")
        else:
            with st.spinner("Building chart..."):
                fig = build_chart(chart_type, active_df, **chart_kwargs)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                    # Export
                    from modules.export import get_chart_download_link
                    png_link = get_chart_download_link(fig, f"custom_{chart_type}", "png")
                    if png_link:
                        st.markdown(png_link, unsafe_allow_html=True)
                else:
                    st.warning(f"Could not create {chart_type} chart with the selected parameters")

# ─── TAB 3: Search Charts ───────────────────────────────────────────
with tab3:
    section_header("🔍 Search Charts by Purpose")
    st.caption("Describe what you want to see, and we'll suggest the right chart")

    search_query = st.text_input("What do you want to visualize?", placeholder="e.g., distribution, trend, correlation, comparison, hierarchy")
    if search_query:
        results = get_chart_search_results(search_query)
        if results:
            st.markdown(f"**Found {len(results)} matching chart types**")
            for chart_type, desc in results:
                with st.container():
                    st.markdown(f"**{chart_type.replace('_', ' ').title()}** — {desc}")
                    # Auto-build with best available columns
                    recs = auto_recommend_chart(active_df)
                    matching_recs = [r for r in recs if r["chart"] == chart_type]
                    if matching_recs:
                        rec = matching_recs[0]
                        chart_kwargs = {k: rec[k] for k in ("x", "y", "color", "size", "z", "path", "values", "dimensions") if rec.get(k) is not None}
                        fig = build_chart(chart_type, active_df, **chart_kwargs, height=300)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                    st.markdown("---")
        else:
            st.info(f"No chart types found matching '{search_query}'. Try: trend, distribution, compare, correlation, hierarchy, composition")

    # Quick links
    st.markdown("### 📌 Quick Links")
    quick_charts = {
        "📊 Distribution": "histogram",
        "📈 Trend Over Time": "line",
        "🔗 Comparison": "bar",
        "🔵 Correlation": "scatter",
        "🥧 Composition": "pie",
        "📦 Outliers": "box",
        "🎯 Multi-Dimension": "parallel_coordinates",
        "🏠 Hierarchy": "treemap",
    }
    cols = st.columns(4)
    for i, (label, chart_type) in enumerate(quick_charts.items()):
        with cols[i % 4]:
            if st.button(label, use_container_width=True):
                recs = auto_recommend_chart(active_df)
                matching = [r for r in recs if r["chart"] == chart_type]
                if matching:
                    rec = matching[0]
                    chart_kwargs = {k: rec[k] for k in ("x", "y", "color", "size", "z", "path", "values", "dimensions") if rec.get(k) is not None}
                    fig = build_chart(chart_type, active_df, **chart_kwargs, height=430)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

