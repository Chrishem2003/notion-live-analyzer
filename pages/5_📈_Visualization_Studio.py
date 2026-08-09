"""
📈 Visualization Studio — Consolidated Visualization & Dashboard Hub (Fully Stabilized & Upgraded)
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


def build_chart(chart_type, df, x=None, y=None, color=None, facet=None, size=None, height=420, **kwargs):
    if not PLOTLY_AVAILABLE or df is None or df.empty:
        return None
    try:
        template = "plotly_dark"
        
        # Merge any extra kwargs into parameters seamlessly
        if "x" in kwargs and not x:
            x = kwargs["x"]
        if "y" in kwargs and not y:
            y = kwargs["y"]
        if "color" in kwargs and not color:
            color = kwargs["color"]

        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        all_cols = df.columns.tolist()
        
        fallback_x = x if x and x in all_cols else (cat_cols[0] if cat_cols else all_cols[0])
        fallback_y = y if y and y in all_cols else (num_cols[0] if num_cols else None)

        if chart_type == "Histogram":
            fig = px.histogram(df, x=fallback_x, color=color if color in all_cols else None, barmode="group", template=template, height=height)
        elif chart_type == "Scatter Plot":
            fig = px.scatter(df, x=fallback_x, y=fallback_y, color=color if color in all_cols else None, size=size if size in all_cols else None, template=template, height=height, trendline="ols" if len(df) > 5 and fallback_y else None)
        elif chart_type == "Bar Chart":
            fig = px.bar(df, x=fallback_x, y=fallback_y, color=color if color in all_cols else None, barmode="group", template=template, height=height)
        elif chart_type == "Line Chart":
            fig = px.line(df, x=fallback_x, y=fallback_y, color=color if color in all_cols else None, markers=True, template=template, height=height)
        elif chart_type == "Area Chart":
            fig = px.area(df, x=fallback_x, y=fallback_y, color=color if color in all_cols else None, template=template, height=height)
        elif chart_type == "Box Plot":
            fig = px.box(df, x=fallback_x, y=fallback_y if fallback_y in all_cols else None, color=color if color in all_cols else None, template=template, height=height)
        elif chart_type == "Violin Plot":
            fig = px.violin(df, x=fallback_x, y=fallback_y if fallback_y in all_cols else None, color=color if color in all_cols else None, box=True, points="all", template=template, height=height)
        elif chart_type == "Pie / Donut":
            counts = df[fallback_x].value_counts().reset_index()
            counts.columns = [fallback_x, "count"]
            fig = px.pie(counts, names=fallback_x, values="count", hole=0.4, template=template, height=height)
        elif chart_type == "Heatmap":
            num_df = df.select_dtypes(include=[np.number])
            if not num_df.empty:
                corr = num_df.corr()
                fig = px.imshow(corr, text_auto=True, color_continuous_scale="Viridis", template=template, height=height)
            else:
                fig = px.bar(df, template=template, height=height)
        elif chart_type == "Treemap":
            vals = num_cols[0] if num_cols else None
            fig = px.treemap(df, path=[fallback_x], values=vals, template=template, height=height)
        elif chart_type == "Sunburst":
            vals = num_cols[0] if num_cols else None
            path = [fallback_x, color] if color and color in all_cols and color != fallback_x else [fallback_x]
            fig = px.sunburst(df, path=path, values=vals, template=template, height=height)
        elif chart_type == "Funnel Chart":
            fig = px.funnel(df, x=fallback_x, y=fallback_y, color=color if color in all_cols else None, template=template, height=height)
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
    except Exception as e:
        st.error(f"⚠️ Chart execution error: {e}")
        return None


def render_custom_builder(df):
    section_header("🎨 Advanced Custom Chart Studio", "Configure multi-dimensional data visualizations with real-time Plotly rendering & direct exports.")

    if not PLOTLY_AVAILABLE:
        st.error("⚠️ Plotly is required for visualization rendering.")
        return

    all_cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

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

    fig = build_chart(
        chart_type, df,
        x=x_col if x_col else None,
        y=y_col if y_col else None,
        color=color_col if color_col else None,
        size=size_col if size_col else None,
        height=height
    )
    
    if fig:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
        st.markdown("#### 📥 Download & Copy Studio Assets")
        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            render_export_buttons(df, base_name=f"custom_viz_{chart_type.lower().replace(' ', '_')}")
        with exp_col2:
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📋 Copy / Download Raw Table CSV",
                data=csv_data,
                file_name="chart_source_data.csv",
                mime="text/csv",
                key="download_raw_csv_custom"
            )
    else:
        st.error("⚠️ Could not render chart with the selected parameters.")


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
            # Pass dictionary unpacking cleanly into the updated build_chart function
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
        fig1 = build_chart("Histogram", df, x=numeric_cols[0], height=340)
        if fig1:
            st.plotly_chart(fig1, use_container_width=True)

    with row1_c2:
        if len(numeric_cols) >= 2:
            fig2 = build_chart("Scatter Plot", df, x=numeric_cols[0], y=numeric_cols[1], height=340)
            if fig2:
                st.plotly_chart(fig2, use_container_width=True)

    if cat_cols and len(numeric_cols) >= 1:
        fig3 = build_chart("Bar Chart", df, x=cat_cols[0], y=numeric_cols[0], height=340)
        if fig3:
            st.plotly_chart(fig3, use_container_width=True)
            
    st.markdown("---")
    render_export_buttons(df, base_name="executive_dashboard_dataset")


def render_deck_builder(df):
    section_header("📽️ Presentation Deck & Slide Generator", "Structure executive presentation slides with embedded charts and narrative metric highlights.")

    deck_title = st.text_input("Presentation Deck Title", value="Executive Analytics & Data Briefing", key="deck_title_input")
    slide_count = st.slider("Number of Slides to Generate", 2, 6, 4, key="deck_slide_count")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

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
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

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

        st.markdown("#### 📋 Extracted Dataset Preview & Copy Options")
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