"""
📈 Visualization Studio — Consolidated Visualization & Dashboard Hub (Upgraded)
Consolidates Advanced Visuals, Executive Dashboard Builder, Presentation Deck Generator,
Chart Data Extractor, and AI Insights Visuals into a high-performance analytics studio.
"""

import numpy as np
import pandas as pd
import streamlit as st

from modules.page_bootstrap import setup_page, render_standard_footer
from modules.session_manager import get_active_dataframe
from modules.shared_ui import (
    hero_card,
    section_header,
    render_dataset_context_banner,
    render_export_buttons,
)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def get_df():
    df = get_active_dataframe()
    if df is None:
        np.random.seed(42)
        return pd.DataFrame({
            "Category": np.random.choice(["Type A", "Type B", "Type C", "Type D"], 120),
            "SubCategory": np.random.choice(["North-East", "South-West", "Central"], 120),
            "Value_A": np.random.normal(55, 12, 120),
            "Value_B": np.random.normal(32, 9, 120),
            "Metric": np.random.uniform(5, 95, 120),
            "Date": pd.date_range(start="2026-01-01", periods=120, freq="D")
        })
    return df


def build_chart(chart_type, df, x, y, color=None, facet=None, size=None, height=420):
    if not PLOTLY_AVAILABLE:
        return None
    try:
        template = "plotly_dark"
        if chart_type == "Histogram" and x:
            fig = px.histogram(df, x=x, color=color, barmode="group", template=template, height=height)
        elif chart_type == "Scatter Plot" and x and y:
            fig = px.scatter(df, x=x, y=y, color=color, size=size, template=template, height=height, trendline="ols" if len(df) > 5 else None)
        elif chart_type == "Bar Chart" and x and y:
            fig = px.bar(df, x=x, y=y, color=color, barmode="group", template=template, height=height)
        elif chart_type == "Line Chart" and x and y:
            fig = px.line(df, x=x, y=y, color=color, markers=True, template=template, height=height)
        elif chart_type == "Area Chart" and x and y:
            fig = px.area(df, x=x, y=y, color=color, template=template, height=height)
        elif chart_type == "Box Plot" and x:
            fig = px.box(df, x=x, y=y, color=color, template=template, height=height)
        elif chart_type == "Violin Plot" and x:
            fig = px.violin(df, x=x, y=y, color=color, box=True, points="all", template=template, height=height)
        elif chart_type == "Pie / Donut" and x:
            counts = df[x].value_counts().reset_index()
            counts.columns = [x, "count"]
            fig = px.pie(counts, names=x, values="count", hole=0.4, template=template, height=height)
        elif chart_type == "Heatmap":
            num_df = df.select_dtypes(include=[np.number])
            if not num_df.empty:
                corr = num_df.corr()
                fig = px.imshow(corr, text_auto=True, color_continuous_scale="Viridis", template=template, height=height)
            else:
                fig = px.bar(df, template=template, height=height)
        elif chart_type == "Treemap" and x:
            vals = df.select_dtypes(include=[np.number]).columns[0] if not df.select_dtypes(include=[np.number]).empty else None
            fig = px.treemap(df, path=[x], values=vals, template=template, height=height)
        elif chart_type == "Sunburst" and x:
            vals = df.select_dtypes(include=[np.number]).columns[0] if not df.select_dtypes(include=[np.number]).empty else None
            path = [x, color] if color and color != x else [x]
            fig = px.sunburst(df, path=path, values=vals, template=template, height=height)
        elif chart_type == "Funnel Chart" and x and y:
            fig = px.funnel(df, x=x, y=y, color=color, template=template, height=height)
        else:
            fig = px.bar(df, template=template, height=height)

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f8fafc", family="Inter, sans-serif"),
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig
    except Exception:
        return None


def render_custom_builder(df):
    section_header("🎨 Advanced Custom Chart Studio", "Configure multi-dimensional data visualizations with real-time Plotly rendering.")

    if not PLOTLY_AVAILABLE:
        st.error("⚠️ Plotly is required for visualization rendering.")
        return

    all_cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    chart_type = st.selectbox("Select Visualization Archetype", [
        "Bar Chart", "Scatter Plot", "Line Chart", "Area Chart", "Histogram",
        "Box Plot", "Violin Plot", "Pie / Donut", "Heatmap", "Treemap",
        "Sunburst", "Funnel Chart"
    ], key="viz_type_advanced")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        x_col = st.selectbox("X-Axis / Dimension", [""] + all_cols, key="viz_x_adv")
    with col2:
        y_col = st.selectbox("Y-Axis / Metric", [""] + all_cols, key="viz_y_adv")
    with col3:
        color_col = st.selectbox("Color / Group By", [""] + all_cols, key="viz_color_adv")
    with col4:
        size_col = st.selectbox("Marker Size (Scatter)", [""] + numeric_cols, key="viz_size_adv")

    height = st.slider("Visualization Height (px)", 300, 750, 450, 25, key="viz_height_adv")

    if st.button("🚀 Render Visual Studio Chart", type="primary", key="render_adv_chart"):
        fig = build_chart(
            chart_type, df,
            x=x_col if x_col else None,
            y=y_col if y_col else None,
            color=color_col if color_col else None,
            size=size_col if size_col else None,
            height=height
        )
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            render_export_buttons(df, base_name=f"visualization_{chart_type.lower().replace(' ', '_')}")
        else:
            st.error("⚠️ Could not render chart with the selected parameters. Verify field mappings.")


def render_auto_studio(df):
    section_header("🤖 AI Auto-Recommendation Studio", "Automated exploratory visual discovery based on active dataset topology.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if not numeric_cols:
        st.warning("⚠️ Dataset requires numeric columns to generate automated visual recommendations.")
        return

    st.markdown("The recommendation engine has scanned your dataset topology and generated these optimal perspectives:")

    recs = []
    if numeric_cols:
        recs.append(("Histogram", {"x": numeric_cols[0]}, f"Univariate Distribution Analysis of '{numeric_cols[0]}'"))
    if len(numeric_cols) >= 2:
        recs.append(("Scatter Plot", {"x": numeric_cols[0], "y": numeric_cols[1]}, f"Bivariate Correlation Study between '{numeric_cols[0]}' and '{numeric_cols[1]}'"))
    if cat_cols and numeric_cols:
        recs.append(("Bar Chart", {"x": cat_cols[0], "y": numeric_cols[0]}, f"Categorical Comparison of '{numeric_cols[0]}' across '{cat_cols[0]}'"))
    if len(numeric_cols) >= 3:
        recs.append(("Heatmap", {}, "Multivariate Correlation Matrix across all numeric features"))

    for i, (ctype, params, rationale) in enumerate(recs):
        with st.container():
            st.markdown(f"#### 💡 Insight Perspective {i+1}: {ctype}")
            st.caption(rationale)
            fig = build_chart(ctype, df, height=350, **params)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            st.markdown("---")


def render_exec_dashboard(df):
    section_header("📊 Executive KPI & Multi-Chart Dashboard", "Assembled executive dashboard combining core metrics, distribution telemetry, and trend analytics.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if not numeric_cols:
        st.warning("⚠️ Insufficient numeric features for executive metrics.")
        return

    st.markdown("#### Key Performance Indicators (KPIs)")
    kpi_cols = st.columns(min(4, len(numeric_cols)))
    for i, col_name in enumerate(numeric_cols[:4]):
        mean_val = df[col_name].mean()
        std_val = df[col_name].std()
        kpi_cols[i].metric(label=f"Avg {col_name}", value=f"{mean_val:,.2f}", delta=f"±{std_val:.2f} σ")

    st.markdown("---")
    st.markdown("#### Multi-Panel Executive Telemetry")
    row1_c1, row1_c2 = st.columns(2)

    with row1_c1:
        fig1 = build_chart("Histogram", df, x=numeric_cols[0], y=None, height=340)
        if fig1:
            st.plotly_chart(fig1, use_container_width=True)

    with row1_c2:
        if len(numeric_cols) >= 2:
            fig2 = build_chart("Scatter Plot", df, x=numeric_cols[0], y=numeric_cols[1], height=340)
            if fig2:
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Additional numeric columns required for scatter correlation.")

    if cat_cols and len(numeric_cols) >= 1:
        fig3 = build_chart("Bar Chart", df, x=cat_cols[0], y=numeric_cols[0], height=340)
        if fig3:
            st.plotly_chart(fig3, use_container_width=True)


def render_deck_builder(df):
    section_header("📽️ Presentation Deck & Slide Generator", "Structure executive presentation slides with embedded charts and narrative metric highlights.")

    deck_title = st.text_input("Presentation Deck Title", value="Executive Analytics & Data Briefing", key="deck_title_input")
    slide_count = st.slider("Number of Slides to Generate", 2, 6, 4, key="deck_slide_count")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = st.select_dtypes(include=["object", "category"]).columns.tolist()

    if st.button("📽️ Generate Presentation Deck", type="primary", key="build_deck_btn"):
        st.success(f"✅ Presentation deck '{deck_title}' compiled successfully with {slide_count} slides.")
        for i in range(slide_count):
            with st.expander(f"Slide {i+1}: Analytical Briefing Panel", expanded=(i == 0)):
                col_metric = numeric_cols[i % len(numeric_cols)] if numeric_cols else "Metric"
                mean_val = df[col_metric].mean() if numeric_cols else 0.0
                st.markdown(f"**Slide Objective:** Present executive insights regarding `{col_metric}` distribution and trends.")
                st.metric(f"Primary Slide Metric ({col_metric})", f"{mean_val:,.2f}")

                if cat_cols and numeric_cols:
                    fig = build_chart("Bar Chart", df, x=cat_cols[i % len(cat_cols)], y=col_metric, height=280)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)


def render_chart_extractor(df):
    section_header("📊 Chart Data Extractor & Aggregator", "Extract, aggregate, and export structured tabular subsets directly from visual nodes.")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = st.select_dtypes(include=["object", "category"]).columns.tolist()

    if not numeric_cols or not cat_cols:
        st.warning("⚠️ Data extraction requires both categorical and numeric columns.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        group_col = st.selectbox("Group By Dimension", cat_cols, key="ext_group")
    with col2:
        agg_col = st.selectbox("Target Metric", numeric_cols, key="ext_agg")
    with col3:
        agg_func = st.selectbox("Aggregation Function", ["mean", "sum", "median", "count", "max", "min", "std"], key="ext_func")

    if st.button("📊 Extract & Process Aggregated Data", type="primary", key="run_extraction"):
        if agg_func == "count":
            extracted_df = df.groupby(group_col)[agg_col].count().reset_index()
        else:
            extracted_df = df.groupby(group_col)[agg_col].agg(agg_func).reset_index()

        st.markdown("#### 📋 Extracted Dataset Preview")
        st.dataframe(extracted_df, use_container_width=True, hide_index=True)
        render_export_buttons(extracted_df, base_name="extracted_chart_dataset")


def main():
    from modules.subscription import require_active_subscription
    require_active_subscription()

    setup_page("Visualization Studio", "📈", initial_sidebar_state="expanded")

    hero_card(
        "📈 Visualization Studio & Executive Dashboard Hub",
        "Consolidated enterprise visualization platform featuring advanced multi-dimensional charting, automated AI recommendations, executive dashboards, presentation slide decks, and chart data extraction.",
        badge_text="VISUALIZATION STUDIO • ENTERPRISE HUB",
    )

    render_dataset_context_banner()

    df = get_df()

    tabs = st.tabs([
        "🎨 Custom Builder",
        "🤖 Auto-Recommendations",
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