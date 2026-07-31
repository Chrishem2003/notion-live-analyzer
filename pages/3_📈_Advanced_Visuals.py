"""
═══════════════════════════════════════════════════════════════════════════════
ADVANCED VISUALS STUDIO [ENTERPRISE EDITION - HIGH CONTRAST]
Standalone Edition featuring Nordic Cyber-Emerald styling, ultra-clear text 
hierarchy, defensive session handling, and modular visualization tools.
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

# Defensive imports for modular systems with local fallbacks
try:
    from modules.chart_builder import build_chart
    from modules.config import CHART_COLOR_PALETTES, init_session_state
    from modules.data_processor import infer_column_types
    from modules.export import get_chart_download_link, render_export_buttons
    from modules.ui_components import hero_card, load_css, section_header, watermark
    from modules.viz_engine import (
        ALL_CHART_TYPES,
        auto_recommend_chart,
        explain_chart_recommendation,
        get_chart_search_results,
    )
except ImportError:
    # ── Fallback Implementations ──
    CHART_COLOR_PALETTES = {
        "Cyber Neon": ["#00f2fe", "#4facfe", "#00f2fe", "#7f00ff"],
        "Viridis": ["#440154", "#21908d", "#fde725"],
        "Plasma": ["#0d0887", "#cc4678", "#f0f921"]
    }
    ALL_CHART_TYPES = [
        "histogram", "line", "bar", "scatter", "pie", "box", 
        "parallel_coordinates", "treemap", "bubble", "scatter_3d"
    ]

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

    def infer_column_types(df):
        types = {}
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                types[col] = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                types[col] = "temporal"
            else:
                types[col] = "categorical"
        return types

    def auto_recommend_chart(df, cols=None):
        cols = cols or df.columns.tolist()
        num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        cat_cols = [c for c in cols if not pd.api.types.is_numeric_dtype(df[c])]
        
        recs = []
        if num_cols:
            recs.append({"chart": "histogram", "x": num_cols[0], "reason": f"Analyze distribution density for {num_cols[0]}."})
        if len(num_cols) >= 2:
            recs.append({"chart": "scatter", "x": num_cols[0], "y": num_cols[1], "reason": f"Evaluate metric correlation between {num_cols[0]} and {num_cols[1]}."})
        if cat_cols and num_cols:
            recs.append({"chart": "bar", "x": cat_cols[0], "y": num_cols[0], "reason": f"Compare categorical aggregates of {num_cols[0]} across {cat_cols[0]}."})
        return recs

    def explain_chart_recommendation(rec):
        return f"**Recommended Architecture:** {rec.get('chart', 'Chart').title()}\n\n*Reasoning:* {rec.get('reason', 'Optimal structure derived from data topology.')}"

    def get_chart_search_results(query):
        q = query.lower()
        results = []
        if "distrib" in q or "hist" in q:
            results.append(("histogram", "Displays numeric value frequencies and variance distribution."))
        if "corr" in q or "scatter" in q or "relationship" in q:
            results.append(("scatter", "Plots bivariate relationships and data clusters."))
        if "comp" in q or "bar" in q or "cat" in q:
            results.append(("bar", "Compares discrete categorical values or metrics."))
        if not results:
            results = [("histogram", "Displays numeric value frequencies."), ("scatter", "Plots bivariate relationships.")]
        return results

    def build_chart(chart_type, df, **kwargs):
        import plotly.express as px
        x = kwargs.get("x")
        y = kwargs.get("y")
        color = kwargs.get("color")
        height = kwargs.get("height", 400)

        try:
            if chart_type == "histogram" and x:
                fig = px.histogram(df, x=x, color=color, height=height, template="plotly_dark")
            elif chart_type == "scatter" and x and y:
                fig = px.scatter(df, x=x, y=y, color=color, height=height, template="plotly_dark")
            elif chart_type == "bar" and x and y:
                fig = px.bar(df, x=x, y=y, color=color, height=height, template="plotly_dark")
            elif chart_type == "line" and x and y:
                fig = px.line(df, x=x, y=y, color=color, height=height, template="plotly_dark")
            elif chart_type == "box" and x:
                fig = px.box(df, x=x, y=y, color=color, height=height, template="plotly_dark")
            else:
                fig = px.bar(df, height=height, template="plotly_dark")
            
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f8fafc")
            )
            return fig
        except Exception:
            return None

    def get_chart_download_link(fig, filename, format_type):
        return f"<span style='color:#00f2fe;'>🔍 [Download {filename}.{format_type} ready]</span>"

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Advanced Visuals Studio [SECURE]",
    layout="wide",
    page_icon="🔍 ",
    initial_sidebar_state="collapsed",
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
    /* Global App Background */
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

    /* Button Customization */
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
        box-shadow: 0 0 12px rgba(0, 242, 254, 0.5);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_card(
    "🔍 World-Class Advanced Visualization Studio [CLASSIFIED]",
    (
        "18+ interactive chart types with CHRISHEM-powered auto-recommendation,"
        " live dataset filtering, statistical aggregation, custom templates, and"
        " publication-ready exports."
    ),
    badge_text="🔍 v5.0  Enterprise Chart Studio & Analytics Engine",
)
watermark("CHRISHEM")

# ─── Data Selection & Validation ──────────────────────────────────────
active_df = st.session_state.get("active_df") or st.session_state.get("working_df") or st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.markdown(
        """
        <div class='contrast-card'>
            <h3 style='margin-top:0;'>⚠️ No Active Dataset Detected</h3>
            <p style='color:#cbd5e1;'>Load a dataset or generate synthetic observations to explore interactive visualizations.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔍 Load Synthetic Biological Dataset", type="primary", use_container_width=True):
            np.random.seed(42)
            sim_df = pd.DataFrame({
                "Gene_Expression_A": np.random.normal(12.5, 2.1, 120),
                "Gene_Expression_B": np.random.normal(8.3, 1.4, 120),
                "Protein_Density": np.random.uniform(0.1, 5.0, 120),
                "Patient_Age": np.random.randint(22, 78, 120),
                "Biomarker_Status": np.random.choice(["Positive", "Negative"], 120),
                "Cohort": np.random.choice(["Control", "Treatment_A", "Treatment_B"], 120)
            })
            st.session_state["active_df"] = sim_df
            st.rerun()
    with col_b:
        if st.button("🔍 Generate Multi-Metric Dataset", use_container_width=True):
            np.random.seed(101)
            sim_df = pd.DataFrame({
                "Metric_Alpha": np.random.randn(150),
                "Metric_Beta": np.random.randn(150),
                "Category": np.random.choice(["Type-1", "Type-2", "Type-3"], 150)
            })
            st.session_state["active_df"] = sim_df
            st.rerun()
    st.stop()

# Get column metadata & categorized lists
col_types = infer_column_types(active_df)
all_columns = active_df.columns.tolist()
numeric_cols = [c for c in all_columns if col_types.get(c) in ("numeric", "integer")]
cat_cols = [c for c in all_columns if col_types.get(c) in ("categorical", "string")]
temporal_cols = [c for c in all_columns if col_types.get(c) == "temporal"]

# ─── Global Dataset Filter & Transformation Controls ──────────────────
with st.expander("🔍 ️ Optional: Dataset Row Filtering & Slice Controls", expanded=False):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_col = st.selectbox(
            "Filter Column (Optional)",
            options=[""] + all_columns,
            key="viz_filter_col",
        )
    with col_f2:
        if filter_col and filter_col in cat_cols:
            unique_vals = active_df[filter_col].dropna().unique().tolist()
            selected_vals = st.multiselect(
                f"Keep values in **{filter_col}**",
                options=unique_vals,
                default=unique_vals[: min(10, len(unique_vals))],
            )
            if selected_vals:
                active_df = active_df[active_df[filter_col].isin(selected_vals)]
        elif filter_col and filter_col in numeric_cols:
            min_v, max_v = float(active_df[filter_col].min()), float(active_df[filter_col].max())
            val_range = st.slider(
                f"Range for **{filter_col}**",
                min_value=min_v,
                max_value=max_v,
                value=(min_v, max_v),
            )
            active_df = active_df[
                (active_df[filter_col] >= val_range[0])
                & (active_df[filter_col] <= val_range[1])
            ]

st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)

# ─── Main Navigation Tabs ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Auto-Recommend AI",
    "🔍 Pro Custom Builder",
    "🔍 Semantic Chart Search",
    "🔍 Multi-Chart Dashboard",
])

# ───────────────────────────────────────────────────────────────────────
# TAB 1: AUTO-RECOMMEND ENGINE
# ───────────────────────────────────────────────────────────────────────
with tab1:
    section_header("🔍 CHRISHEM-Powered Automated Chart Studio")
    st.caption(
        "Select columns below to let the automated recommendation engine compute"
        " and render the highest-impact visual configurations."
    )

    col_sel1, col_sel2 = st.columns([3, 1])
    with col_sel1:
        selected_cols = st.multiselect(
            "Select Target Columns to Analyze",
            options=all_columns,
            default=(numeric_cols[:2] + cat_cols[:1] if numeric_cols else all_columns[:3]),
            key="auto_rec_multiselect",
            help="Engine evaluates distribution, correlation, and cardinality across columns.",
        )
    with col_sel2:
        max_recs = st.number_input(
            "Max Recommendations", min_value=1, max_value=12, value=6, step=1
        )

    if selected_cols:
        recommendations = auto_recommend_chart(active_df, selected_cols)

        if recommendations:
            st.markdown(f"**Successfully generated {min(len(recommendations), max_recs)} tailored visualization option(s)**")
            for i, rec in enumerate(recommendations[:max_recs]):
                with st.container():
                    st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)
                    col_exp, col_chart = st.columns([1, 2])

                    with col_exp:
                        st.markdown(explain_chart_recommendation(rec))
                        chart_type = rec["chart"]
                        st.caption(f"🔍 Architecture: `{chart_type.replace('_', ' ').title()}`")

                        chart_kwargs = {
                            k: rec[k]
                            for k in ("x", "y", "color", "size", "z", "path", "values", "dimensions")
                            if rec.get(k) is not None
                        }
                        rec_fig = build_chart(chart_type, active_df, **chart_kwargs, height=320)
                        if rec_fig:
                            dl_link = get_chart_download_link(rec_fig, f"recommended_{chart_type}_{i}", "png")
                            if dl_link:
                                st.markdown(dl_link, unsafe_allow_html=True)

                    with col_chart:
                        if rec_fig:
                            st.plotly_chart(rec_fig, use_container_width=True)
                        else:
                            st.info(f"⚠️ Could not build `{chart_type}` with the selected column parameters.")
        else:
            st.info("🔍 No recommendations available for this exact column combination. Try selecting a mix of numeric and categorical variables.")
    else:
        st.info("🔍 Please select at least one column above to trigger automated chart recommendations.")

# ───────────────────────────────────────────────────────────────────────
# TAB 2: PRO CUSTOM CHART BUILDER
# ───────────────────────────────────────────────────────────────────────
with tab2:
    section_header("🔍 Enterprise Custom Chart Builder")
    st.caption("Full parameter control over chart geometry, mapping axes, color palettes, and dimensions.")

    col1, col2, col3 = st.columns(3)

    with col1:
        chart_type = st.selectbox(
            "Chart Architecture Type",
            options=ALL_CHART_TYPES,
            index=0,
            format_func=lambda x: str(x).replace("_", " ").title(),
            key="custom_chart_type_select",
        )
        x_col = st.selectbox(
            "X-Axis / Category Column",
            options=[""] + all_columns,
            index=0,
            key="custom_x",
        )

    with col2:
        y_col = st.selectbox(
            "Y-Axis / Metric Column",
            options=[""] + all_columns,
            index=0,
            key="custom_y",
        )
        color_col = st.selectbox(
            "Color Grouping Variable",
            options=[""] + all_columns,
            index=0,
            key="custom_color",
        )

    with col3:
        size_col = st.selectbox(
            "Bubble Size Variable (Numeric)",
            options=[""] + numeric_cols,
            index=0,
            key="custom_size",
        )
        z_col = st.selectbox(
            "Z-Axis Variable (3D Plots)",
            options=[""] + numeric_cols,
            index=0,
            key="custom_z",
        )

    with st.expander("⚙️ Advanced Styling & Layout Configuration", expanded=False):
        col_st1, col_st2, col_st3 = st.columns(3)
        with col_st1:
            palette = st.selectbox(
                "Color Palette Scheme",
                options=list(CHART_COLOR_PALETTES.keys()),
                index=0,
                key="custom_palette",
            )
        with col_st2:
            height = st.slider(
                "Chart Canvas Height (px)",
                min_value=350,
                max_value=850,
                value=500,
                step=25,
                key="custom_height",
            )
        with col_st3:
            trendline_option = st.selectbox(
                "Statistical Trendline (Scatter)",
                options=["None", "ols", "lowess"],
                index=0,
                key="custom_trendline",
            )

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

    if st.button("🔍 Render Custom Chart Studio Output", type="primary", use_container_width=True):
        if not x_col and not y_col:
            st.warning("⚠️ Please select at least an X-axis or Y-axis column to build the visualization.")
        else:
            with st.spinner("Rendering high-performance interactive plot..."):
                fig = build_chart(chart_type, active_df, **chart_kwargs)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)
                    section_header("🔍 Export High-Resolution Visual")
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
    st.caption("Describe your analytical objective (e.g., 'distribution', 'correlation', 'comparison'), and the engine will map the optimal chart type.")

    search_query = st.text_input(
        "Enter analytical objective or keyword",
        placeholder="e.g., compare categories, show composition, distribution",
        key="chart_search_input",
    )

    if search_query:
        results = get_chart_search_results(search_query)
        if results:
            st.markdown(f"**Found {len(results)} matching chart architecture(s)**")
            for chart_type, desc in results:
                with st.container():
                    st.markdown(f"### 🔍 {chart_type.replace('_', ' ').title()}")
                    st.caption(desc)

                    recs = auto_recommend_chart(active_df)
                    matching_recs = [r for r in recs if r["chart"] == chart_type]
                    if matching_recs:
                        rec = matching_recs[0]
                        sub_kwargs = {
                            k: rec[k]
                            for k in ("x", "y", "color", "size", "z", "path", "values", "dimensions")
                            if rec.get(k) is not None
                        }
                        fig_prev = build_chart(chart_type, active_df, **sub_kwargs, height=350)
                        if fig_prev:
                            st.plotly_chart(fig_prev, use_container_width=True)
                    else:
                        st.info(f"ℹ️ Quick preview not available for `{chart_type}` with current dataset schema.")
                    st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)
        else:
            st.warning(f"⚠️ No matching chart type found for '{search_query}'. Try keywords like: distribution, comparison, correlation.")

    st.markdown("### 🔍 Quick-Access Standard Visualizations")
    quick_charts = {
        "🔍 Distribution": "histogram",
        "🔍 Trend Over Time": "line",
        "🔍 Category Comparison": "bar",
        "🔍 Scatter Correlation": "scatter",
        "🔍 Proportional Composition": "pie",
        "🔍 Statistical Box Plot": "box",
        "🔍 Multi-Dimension Matrix": "parallel_coordinates",
        "🔍 Hierarchical Treemap": "treemap",
    }

    q_cols = st.columns(4)
    for i, (label, chart_type) in enumerate(quick_charts.items()):
        with q_cols[i % 4]:
            if st.button(label, use_container_width=True, key=f"quick_btn_{chart_type}"):
                recs = auto_recommend_chart(active_df)
                matching = [r for r in recs if r["chart"] == chart_type]
                if matching:
                    rec = matching[0]
                    q_kwargs = {
                        k: rec[k]
                        for k in ("x", "y", "color", "size", "z", "path", "values", "dimensions")
                        if rec.get(k) is not None
                    }
                    q_fig = build_chart(chart_type, active_df, **q_kwargs, height=450)
                    if q_fig:
                        st.plotly_chart(q_fig, use_container_width=True)
                else:
                    st.info(f"⚠️ Unable to generate `{chart_type}` automatically with current data types.")

# ───────────────────────────────────────────────────────────────────────
# TAB 4: MULTI-CHART DASHBOARD VIEW
# ───────────────────────────────────────────────────────────────────────
with tab4:
    section_header("🔍 Multi-Chart Executive Dashboard")
    st.markdown("Simultaneous side-by-side rendering of key dataset metrics and distributions.")

    if len(numeric_cols) >= 2:
        col_d1, col_d2 = st.columns(2)

        with col_d1:
            st.markdown(f"**Primary Metric Distribution: `{numeric_cols[0]}`**")
            fig_d1 = build_chart("histogram", active_df, x=numeric_cols[0], height=350)
            if fig_d1:
                st.plotly_chart(fig_d1, use_container_width=True)

        with col_d2:
            st.markdown(f"**Secondary Correlation: `{numeric_cols[0]}` vs `{numeric_cols[1]}`**")
            fig_d2 = build_chart("scatter", active_df, x=numeric_cols[0], y=numeric_cols[1], height=350)
            if fig_d2:
                st.plotly_chart(fig_d2, use_container_width=True)
    else:
        st.info("ℹ️ Multi-chart executive dashboard requires at least 2 numeric columns in the dataset.")

