"""
📈 Visualization Studio — Consolidated Visualization & Dashboard Hub
Consolidates old pages: 3 (Advanced Visuals), 12 (Dashboard Builder), 18 (Presentation Deck),
37 (Chart Data Extractor), 56 (AI Insights visuals).
"""

import numpy as np
import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
    render_export_buttons,
)


def get_df():
    df = get_active_dataframe()
    if df is None:
        np.random.seed(42)
        return pd.DataFrame({
            "Category": np.random.choice(["A", "B", "C", "D"], 100),
            "Value_A": np.random.normal(50, 15, 100),
            "Value_B": np.random.normal(30, 10, 100),
            "Region": np.random.choice(["North", "South", "East"], 100),
            "Metric": np.random.uniform(0, 100, 100),
        })
    return df


def build_chart(chart_type, df, x, y, color, height=400):
    if not PLOTLY_AVAILABLE:
        return None
    try:
        if chart_type == "Histogram" and x:
            fig = px.histogram(df, x=x, color=color if color else None, template="plotly_dark", height=height)
        elif chart_type == "Scatter Plot" and x and y:
            fig = px.scatter(df, x=x, y=y, color=color if color else None, template="plotly_dark", height=height)
        elif chart_type == "Bar Chart" and x and y:
            fig = px.bar(df, x=x, y=y, color=color if color else None, template="plotly_dark", height=height)
        elif chart_type == "Line Chart" and x and y:
            fig = px.line(df, x=x, y=y, color=color if color else None, template="plotly_dark", height=height)
        elif chart_type == "Box Plot" and x:
            fig = px.box(df, x=x, y=y if y else None, color=color if color else None, template="plotly_dark", height=height)
        elif chart_type == "Pie Chart" and x:
            counts = df[x].value_counts().reset_index()
            counts.columns = [x, "count"]
            fig = px.pie(counts, names=x, values="count", template="plotly_dark", height=height)
        elif chart_type == "Heatmap" and x and y:
            pivot = pd.crosstab(df[x], df[y]) if y != x else df.select_dtypes("number").corr()
            fig = px.imshow(pivot, text_auto=True, template="plotly_dark", height=height)
        elif chart_type == "Treemap" and x:
            fig = px.treemap(df, path=[x], values=df.select_dtypes("number").columns[0] if not df.select_dtypes("number").empty else None, template="plotly_dark", height=height)
        else:
            fig = px.bar(df, template="plotly_dark", height=height)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#f8fafc"))
        return fig
    except Exception:
        return None


def render_custom_builder(df):
    """Tab: Custom chart builder."""
    section_header("🎨 Custom Chart Builder", "Build any chart from the active dataset.")

    all_cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    chart_type = st.selectbox("Chart Type", [
        "Histogram", "Scatter Plot", "Bar Chart", "Line Chart", "Box Plot", "Pie Chart", "Heatmap", "Treemap",
    ], key="viz_chart_type")

    c1, c2, c3 = st.columns(3)
    with c1:
        x_col = st.selectbox("X-Axis", [""] + all_cols, key="viz_x")
    with c2:
        y_col = st.selectbox("Y-Axis", [""] + all_cols, key="viz_y")
    with c3:
        color_col = st.selectbox("Color / Group By", [""] + cat_cols, key="viz_color")

    height = st.slider("Chart Height", 250, 700, 400, 50, key="viz_height")

    if st.button("📊 Render Chart", type="primary", key="render_chart"):
        fig = build_chart(
            chart_type, df,
            x=x_col if x_col else None,
            y=y_col if y_col else None,
            color=color_col if color_col else None,
            height=height,
        )
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Could not render chart. Check your selections.")


def render_auto_studio(df):
    """Tab: Auto-recommendation studio."""
    section_header("🤖 Auto-Recommendation Studio", "Automated chart suggestions based on data topology.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if not numeric_cols:
        st.info("Need numeric columns for auto-recommendation.")
        return

    recs = []
    if numeric_cols:
        recs.append(("Histogram", {"x": numeric_cols[0]}, "Analyze distribution of first numeric feature"))
    if len(numeric_cols) >= 2:
        recs.append(("Scatter Plot", {"x": numeric_cols[0], "y": numeric_cols[1]}, "Explore correlation between two metrics"))
    if cat_cols and numeric_cols:
        recs.append(("Bar Chart", {"x": cat_cols[0], "y": numeric_cols[0]}, "Compare metric across categories"))

    for i, (ctype, params, reason) in enumerate(recs):
        st.markdown(f"#### Recommendation {i+1}: {ctype}")
        st.caption(reason)
        fig = build_chart(ctype, df, color=None, height=300, **params)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('<div class="chris-hr"></div>', unsafe_allow_html=True)


def render_exec_dashboard(df):
    """Tab: Multi-chart executive dashboard."""
    section_header("📊 Executive Dashboard", "Multi-chart KPI dashboard assembled from the active dataset.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if not numeric_cols:
        st.info("Need numeric columns for the dashboard.")
        return

    # KPI metrics
    cols = st.columns(min(4, len(numeric_cols)))
    for i, col in enumerate(cols):
        col.metric(f"{numeric_cols[i]} Mean", f"{df[numeric_cols[i]].mean():,.2f}")

    # Charts grid
    grid_cols = st.columns(2)
    with grid_cols[0]:
        fig1 = build_chart("Histogram", df, x=numeric_cols[0], y=None, color=None, height=320)
        if fig1:
            st.plotly_chart(fig1, use_container_width=True)
    with grid_cols[1]:
        if len(numeric_cols) >= 2:
            fig2 = build_chart("Scatter Plot", df, x=numeric_cols[0], y=numeric_cols[1], color=None, height=320)
            if fig2:
                st.plotly_chart(fig2, use_container_width=True)

    if cat_cols and numeric_cols:
        fig3 = build_chart("Bar Chart", df, x=cat_cols[0], y=numeric_cols[0], color=None, height=320)
        if fig3:
            st.plotly_chart(fig3, use_container_width=True)


def render_deck_builder(df):
    """Tab: Presentation deck builder."""
    section_header("📽️ Presentation Deck Builder", "Assemble presentation slides from charts and data insights.")

    st.info("Design presentation slides by selecting charts and summary content. Export the deck for sharing.")

    deck_title = st.text_input("Deck Title", value="CHRISHEM Data Insights", key="deck_title")
    slide_count = st.slider("Number of Slides", 1, 8, 4, key="deck_slides")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if st.button("📽️ Build Presentation Deck", type="primary", key="build_deck"):
        st.success(f"✅ Deck '{deck_title}' with {slide_count} slides built.")
        for i in range(slide_count):
            with st.expander(f"Slide {i+1}", expanded=i == 0):
                st.markdown(f"**Slide {i+1}:** Key insights from active dataset")
                if numeric_cols:
                    st.metric(f"Metric {numeric_cols[i % len(numeric_cols)]} Overview", f"{df[numeric_cols[i % len(numeric_cols)]].mean():,.2f}")
                if cat_cols and numeric_cols:
                    fig = build_chart("Bar Chart", df, x=cat_cols[i % len(cat_cols)], y=numeric_cols[i % len(numeric_cols)], color=None, height=250)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)


def render_chart_extractor(df):
    """Tab: Chart data extractor."""
    section_header("📊 Chart Data Extractor", "Extract data from charts, tables, or aggregated views.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if not numeric_cols or not cat_cols:
        st.info("Need both categorical and numeric columns.")
        return

    group_col = st.selectbox("Group By", cat_cols, key="extract_group")
    agg_col = st.selectbox("Aggregate Metric", numeric_cols, key="extract_agg")
    agg_func = st.selectbox("Aggregation", ["sum", "mean", "median", "count", "max", "min"], key="extract_func")

    if st.button("📊 Extract Aggregated Data", type="primary", key="run_extract"):
        if agg_func == "count":
            result = df.groupby(group_col)[agg_col].count().reset_index()
        else:
            result = df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
        st.dataframe(result, use_container_width=True, hide_index=True)
        render_export_buttons(result, base_name="extracted_chart_data")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()  # paywall/trial gate, real DB check

    setup_page("Visualization Studio", "📈", initial_sidebar_state="expanded")

    hero_card(
        "📈 Visualization Studio",
        "Consolidated visualization hub: custom chart builder, auto-recommendations, executive dashboards, presentation decks, and chart data extraction.",
        badge_text="VISUALIZATION STUDIO • CONSOLIDATED HUB",
    )

    render_dataset_context_banner()

    df = get_df()

    tabs = st.tabs([
        "🎨 Custom Builder",
        "🤖 Auto-Studio",
        "📊 Executive Dashboard",
        "📽️ Presentation Deck",
        "📊 Chart Data Extractor",
    ])

    with tabs[0]:
        render_custom_builder(df)
    with tabs[1]:
        render_auto_studio(df)
    with tabs[2]:
        render_exec_dashboard(df)
    with tabs[3]:
        render_deck_builder(df)
    with tabs[4]:
        render_chart_extractor(df)

    render_standard_footer("VISUALIZATION STUDIO")


if __name__ == "__main__":
    main()
