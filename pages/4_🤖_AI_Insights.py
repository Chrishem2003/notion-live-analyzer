"""
🤖 CHRISHEM Insights Page — Automated data analysis, profiling, and smart recommendations.
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="CHRISHEM Insights", layout="wide", page_icon="🤖")

from modules.config import init_session_state
from modules.ui_components import hero_card, section_header, load_css, watermark, insight_card
from modules.ai_analyzer import CHRISHEMAnalyzer
from modules.data_processor import profile_dataset
from modules.chart_builder import build_chart
from modules.report_generator import auto_generate_report, get_report_download_link
from modules.export import render_export_buttons

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")
hero_card("🤖 CHRISHEM Insights Engine", "Automated data profiling, statistical recommendations, and natural language insights.", "CHRISHEM-Powered Analysis")
watermark("CHRISHEM")

# ─── Data Selection ──────────────────────────────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ No data available. Connect to Notion or upload a file first.")
    st.stop()

st.info(f"**Analyzing**: {len(active_df):,} rows × {len(active_df.columns)} columns")

# ─── Run Full Automated Analysis ─────────────────────────────────────
if st.button("🚀 Run Full Automated Analysis", type="primary", use_container_width=True):
    analyzer = CHRISHEMAnalyzer()

    with st.spinner("🔄 Running comprehensive analysis... This may take a moment."):
        results = analyzer.auto_analyze(active_df)

    # ─── 1. Dataset Profile ────────────────────────────────────────
    section_header("📊 Dataset Profile")
    if "profile" in results:
        profile = results["profile"]
        st.markdown(profile.get("summary", ""))

        # Type summary
        if "type_summary" in profile:
            for dtype, cols in profile["type_summary"].items():
                with st.expander(f"**{dtype}** ({len(cols)} columns)"):
                    for col in cols:
                        st.markdown(f"- {col}")

    # ─── 2. Missing Values ─────────────────────────────────────────
    section_header("⬜ Missing Value Analysis")
    if "missing" in results:
        missing = results["missing"]
        if missing.get("has_missing"):
            insight_card("⚠️", missing.get("message", ""))
            if "data" in missing and missing["data"] is not None and not missing["data"].empty:
                st.dataframe(missing["data"], use_container_width=True, hide_index=True)
            if "suggestions" in missing:
                for s in missing["suggestions"]:
                    insight_card("💡", s)
        else:
            insight_card("✅", "No missing values found in the dataset.")

    # ─── 3. Outliers ───────────────────────────────────────────────
    section_header("🔍 Outlier Detection")
    if "outliers" in results:
        outliers = results["outliers"]
        insight_card("🔍", outliers.get("summary", ""))
        if "details" in outliers and outliers["details"]:
            with st.expander("View outlier details"):
                for col, details in outliers["details"].items():
                    st.markdown(f"**{col}**: IQR={details['iqr_count']} ({details['iqr_pct']}%), z-score={details['zscore_count']} ({details['zscore_pct']}%)")
                    if details.get("top_outliers"):
                        st.markdown(f"  Top outliers: {details['top_outliers'][:5]}")

    # ─── 4. Normality ──────────────────────────────────────────────
    section_header("📈 Normality Test Results")
    if "normality" in results:
        norm = results["normality"]
        insight_card("📈", norm.get("summary", ""))
        if norm.get("normal"):
            with st.expander("✅ Normally distributed variables"):
                for col in norm["normal"]:
                    st.markdown(f"- {col}")
        if norm.get("non_normal"):
            with st.expander("❌ Non-normally distributed variables"):
                for col in norm["non_normal"]:
                    st.markdown(f"- {col}")

    # ─── 5. Correlations ───────────────────────────────────────────
    section_header("🔗 Correlation Discovery")
    if "correlations" in results:
        corr = results["correlations"]
        insight_card("🔗", corr.get("summary", ""))
        if "strong_correlations" in corr and corr["strong_correlations"]:
            corr_df = pd.DataFrame(corr["strong_correlations"])
            st.dataframe(corr_df, use_container_width=True, hide_index=True)

    # ─── 6. Test Recommendations ───────────────────────────────────
    section_header("🎯 Recommended Statistical Tests")
    if "recommendations" in results:
        recs = results["recommendations"]
        if recs:
            for rec in recs:
                with st.container():
                    st.markdown(f"**{rec.get('test', 'Unknown Test')}**")
                    st.markdown(f"_{rec.get('description', '')}_")
                    st.caption(f"📋 **When to use**: {rec.get('when_to_use', '')}")
                    st.caption(f"✅ **Prerequisites**: {rec.get('prerequisites', '')}")
                    st.markdown("---")
        else:
            insight_card("ℹ️", "No specific test recommendations for the current data structure.")

    # ─── 7. Natural Language Insights ──────────────────────────────
    section_header("💡 Key Insights")
    if "insights" in results:
        insights = results["insights"]
        for insight in insights:
            insight_card("💡", insight)

    # ─── 8. Visualizations ─────────────────────────────────────────
    section_header("🎨 Recommended Visualizations")
    if "visualizations" in results:
        viz_recs = results["visualizations"]
        if viz_recs:
            cols = st.columns(3)
            for i, rec in enumerate(viz_recs[:6]):
                with cols[i % 3]:
                    chart_name = rec.get("chart", "").replace("_", " ").title()
                    reason = rec.get("reason", "")
                    st.markdown(f"**📈 {chart_name}**")
                    st.caption(reason)
                    chart_kwargs = {k: rec[k] for k in ("x", "y", "color", "size", "z", "path", "values", "dimensions") if rec.get(k) is not None}
                    chart = build_chart(rec["chart"], active_df, **chart_kwargs, height=300)
                    if chart:
                        st.plotly_chart(chart, use_container_width=True)

    # ─── 9. Generate Report ────────────────────────────────────────
    section_header("📄 Generate Report")
    st.caption("Download a complete analysis report in Markdown, HTML, or PDF format")

    col1, col2, col3 = st.columns(3)
    if col1.button("📥 Download Markdown Report", use_container_width=True):
        report = auto_generate_report(active_df, profile_dataset(active_df), [], results.get("insights", []))
        link = get_report_download_link(report, "md")
        if link:
            st.markdown(link, unsafe_allow_html=True)

    if col2.button("📥 Download HTML Report", use_container_width=True):
        report = auto_generate_report(active_df, profile_dataset(active_df), [], results.get("insights", []))
        link = get_report_download_link(report, "html")
        if link:
            st.markdown(link, unsafe_allow_html=True)

    if col3.button("📥 Download PDF Report", use_container_width=True):
        report = auto_generate_report(active_df, profile_dataset(active_df), [], results.get("insights", []))
        link = get_report_download_link(report, "pdf")
        if link:
            st.markdown(link, unsafe_allow_html=True)

else:
    st.info("👆 Click **'Run Full Automated Analysis'** above to start the CHRISHEM-powered analysis pipeline.")
    st.markdown("""
    ### What this will do:
    1. **Profile** your dataset (rows, columns, types)
    2. **Detect missing values** and suggest remedies
    3. **Find outliers** using IQR and Z-score methods
    4. **Test normality** of numeric variables
    5. **Discover correlations** between variables
    6. **Recommend statistical tests** based on your data structure
    7. **Generate natural language insights** about key patterns
    8. **Suggest visualizations** that best represent your data
    9. **Generate a downloadable report** with all findings
    """)

