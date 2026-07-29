st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""
🤖 CHRISHEM Enterprise Intelligence Engine — World-Class Automated Analysis, Deep Statistical
Problem Solving, Automated Cleaning Recommendations, Predictive Modeling Diagnostics, and Report Export.
"""
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="CHRISHEM Intelligence Hub [SECURE]", layout="wide", page_icon="🤖")

import sys
from pathlib import Path

# ─── ULTIMATE PATH RESOLUTION ────────────────────────────────────────
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(current_file.parent) not in sys.path:
    sys.path.insert(0, str(current_file.parent))

from modules.config import init_session_state
from modules.ui_components import hero_card, section_header, load_css, watermark, insight_card
from modules.ai_analyzer import CHRISHEMAnalyzer
from modules.data_processor import profile_dataset, infer_column_types
from modules.chart_builder import build_chart
from modules.report_generator import auto_generate_report, get_report_download_link

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "🤖 CHRISHEM Enterprise Intelligence & Problem-Solving Hub",
    "Advanced automated data diagnosis, statistical anomaly identification, data-cleaning prescriptors, "
    "and predictive variable engineering powered by CHRISHEM intelligence algorithms.",
    badge_text="🔒 v5.0 — Autonomous Problem Solver & Diagnostics"
)
watermark("CHRISHEM")

# ─── Data Selection & Validation ──────────────────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is None or active_df.empty:
    st.warning("⚠️ No active dataset available. Load data via the File Analyzer or Notion workspace first.")
    st.stop()

# Quick metrics summary bar
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Total Records (Rows)", f"{len(active_df):,}")
col_m2.metric("Total Features (Columns)", f"{len(active_df.columns):,}")
col_m3.metric("Missing Cell Count", f"{active_df.isna().sum().sum():,}")
col_m4.metric("Estimated Memory Footprint", f"{active_df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

st.markdown("---")

# ─── Execution Control Center ─────────────────────────────────────────
col_act1, col_act2 = st.columns([3, 1])
with col_act1:
    st.markdown("### 🧠 Autonomous Diagnostic & Problem-Solving Pipeline")
    st.caption("Executes end-to-end data profiling, anomaly detection, automated data-cleaning recipes, and statistical inference.")
with col_act2:
    run_analysis = st.button("🚀 Run Autonomous Engine", type="primary", use_container_width=True)

# Session state persistence for results
if run_analysis or "analysis_results" not in st.session_state:
    analyzer = CHRISHEMAnalyzer()
    with st.spinner("🔄 Running deep analysis, anomaly triage, and statistical evaluations..."):
        st.session_state["analysis_results"] = analyzer.auto_analyze(active_df)

results = st.session_state.get("analysis_results", {})

if results:
    # ─── SUB-NAVIGATION TABS FOR DEEP PROBLEM SOLVING ─────────────────
    tab_prof, tab_clean, tab_stat, tab_pred, tab_viz, tab_rep = st.tabs([
        "📊 Dataset Health & Profile",
        "🧹 Automated Data Cleaning",
        "📐 Statistical Diagnostics",
        "🎯 Predictive AI Recommendations",
        "📈 Autonomous Visualizations",
        "📄 Executive Reports"
    ])

    # ──────────────────────────────────────────────────────────────────
    # TAB 1: DATASET HEALTH & PROFILE
    # ──────────────────────────────────────────────────────────────────
    with tab_prof:
        section_header("📊 Structural Dataset Health Profile")
        if "profile" in results:
            profile = results["profile"]
            st.markdown(profile.get("summary", ""))

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown("#### 📋 Column Schema Classification")
                if "type_summary" in profile:
                    for dtype, cols in profile["type_summary"].items():
                        with st.expander(f"**{dtype.upper()}** — ({len(cols)} columns)"):
                            for col in cols:
                                st.markdown(f"- `{col}`")
            with col_p2:
                st.markdown("#### ⬜ Missing Data Distribution Breakdown")
                missing_s = active_df.isna().sum()
                missing_s = missing_s[missing_s > 0]
                if not missing_s.empty:
                    miss_df = pd.DataFrame({"Missing Count": missing_s, "Percentage (%)": (missing_s / len(active_df)) * 100})
                    st.dataframe(miss_df, use_container_width=True)
                else:
                    insight_card("✅", "Zero missing values detected across all columns. Data integrity is optimal.")

    # ──────────────────────────────────────────────────────────────────
    # TAB 2: AUTOMATED DATA CLEANING & FIXES
    # ──────────────────────────────────────────────────────────────────
    with tab_clean:
        section_header("🧹 Automated Data Cleaning & Anomaly Prescriptions")
        st.caption("CHRISHEM engine detects data corruptions, cardinality imbalances, and outliers, offering one-click remediation recipes.")

        # Missing values remediation
        if "missing" in results:
            missing = results["missing"]
            if missing.get("has_missing"):
                insight_card("⚠️", missing.get("message", ""))
                if "suggestions" in missing:
                    for s in missing["suggestions"]:
                        insight_card("💡 Prescription", s)
                
                # Interactive Quick Fix Widget
                st.markdown("#### 🛠️ Interactive Cleaning Actions")
                col_cl1, col_cl2 = st.columns(2)
                with col_cl1:
                    if st.button("🧹 Drop Rows with Any Missing Values", use_container_width=True):
                        st.session_state["active_df"] = active_df.dropna()
                        st.success("✅ Cleaned dataset: Dropped rows with missing values. Refresh to view updates.")
                        st.rerun()
                with col_cl2:
                    if st.button("📊 Impute Missing Numerics with Median", use_container_width=True):
                        num_cols_to_fill = active_df.select_dtypes(include=[np.number]).columns
                        active_df[num_cols_to_fill] = active_df[num_cols_to_fill].fillna(active_df[num_cols_to_fill].median())
                        st.session_state["active_df"] = active_df
                        st.success("✅ Cleaned dataset: Imputed numeric columns with median values.")
                        st.rerun()
            else:
                insight_card("✅", "No cleaning required for missing values.")

        # Outliers section
        st.markdown("---")
        section_header("🔍 Advanced Outlier Triage (IQR & Z-Score)")
        if "outliers" in results:
            outliers = results["outliers"]
            insight_card("🔍", outliers.get("summary", ""))
            if "details" in outliers and outliers["details"]:
                with st.expander("🔬 View Detailed Outlier Statistics per Feature"):
                    for col, details in outliers["details"].items():
                        st.markdown(f"**{col}**: IQR Outliers = {details['iqr_count']} ({details['iqr_pct']}%), Z-Score Outliers = {details['zscore_count']} ({details['zscore_pct']}%)")
                        if details.get("top_outliers"):
                            st.caption(f"Extreme values detected: {details['top_outliers'][:5]}")

    # ──────────────────────────────────────────────────────────────────
    # TAB 3: STATISTICAL DIAGNOSTICS & CORRELATIONS
    # ──────────────────────────────────────────────────────────────────
    with tab_stat:
        section_header("📐 Statistical Normality & Correlation Mapping")
        
        col_st1, col_st2 = st.columns(2)
        with col_st1:
            st.markdown("#### 📈 Normality Testing (Shapiro / Distribution Check)")
            if "normality" in results:
                norm = results["normality"]
                insight_card("📈", norm.get("summary", ""))
                if norm.get("normal"):
                    with st.expander("✅ Normally Distributed Features"):
                        for col in norm["normal"]:
                            st.markdown(f"- `{col}`")
                if norm.get("non_normal"):
                    with st.expander("❌ Non-Normal Features (Require Transformation)"):
                        for col in norm["non_normal"]:
                            st.markdown(f"- `{col}`")

        with col_st2:
            st.markdown("#### 🔗 Strong Feature Correlations")
            if "correlations" in results:
                corr = results["correlations"]
                insight_card("🔗", corr.get("summary", ""))
                if "strong_correlations" in corr and corr["strong_correlations"]:
                    corr_df = pd.DataFrame(corr["strong_correlations"])
                    st.dataframe(corr_df, use_container_width=True, hide_index=True)

    # ──────────────────────────────────────────────────────────────────
    # TAB 4: PREDICTIVE AI RECOMMENDATIONS
    # ──────────────────────────────────────────────────────────────────
    with tab_pred:
        section_header("🎯 CHRISHEM Predictive Test & Modeling Recommendations")
        st.caption("Engineered statistical tests and machine learning pipelines suited to your specific schema architecture.")

        if "recommendations" in results:
            recs = results["recommendations"]
            if recs:
                for i, rec in enumerate(recs):
                    with st.container():
                        st.markdown(f"### 📋 Recommendation {i+1}: {rec.get('test', 'Statistical Test')}")
                        st.markdown(f"_{rec.get('description', '')}_")
                        st.info(f"**When to use**: {rec.get('when_to_use', '')}")
                        st.success(f"**Prerequisites & Assumptions**: {rec.get('prerequisites', '')}")
                        st.markdown("---")
            else:
                insight_card("ℹ️", "No specialized predictive test recommendations for this dataset structure.")

    # ──────────────────────────────────────────────────────────────────
    # TAB 5: AUTONOMOUS VISUALIZATIONS
    # ──────────────────────────────────────────────────────────────────
    with tab_viz:
        section_header("📈 Autonomous Visual Render Engine")
        st.markdown("Charts dynamically generated based on feature importance and statistical fit.")

        if "visualizations" in results:
            viz_recs = results["visualizations"]
            if viz_recs:
                v_cols = st.columns(2)
                for i, rec in enumerate(viz_recs[:6]):
                    with v_cols[i % 2]:
                        chart_name = rec.get("chart", "").replace("_", " ").title()
                        reason = rec.get("reason", "")
                        st.markdown(f"**📊 {chart_name}**")
                        st.caption(f"🧠 *{reason}*")
                        
                        chart_kwargs = {k: rec[k] for k in ("x", "y", "color", "size", "z", "path", "values", "dimensions") if rec.get(k) is not None}
                        chart = build_chart(rec["chart"], active_df, **chart_kwargs, height=350)
                        if chart:
                            st.plotly_chart(chart, use_container_width=True)
                        st.markdown("---")

    # ──────────────────────────────────────────────────────────────────
    # TAB 6: EXECUTIVE REPORTS
    # ──────────────────────────────────────────────────────────────────
    with tab_rep:
        section_header("📄 Executive Report Generation & Export")
        st.caption("Compile all diagnostics, findings, cleaning logs, and recommendations into publication-ready formats.")

        col_rep1, col_rep2, col_rep3 = st.columns(3)
        
        report_content = auto_generate_report(active_df, profile_dataset(active_df), [], results.get("insights", []))

        with col_rep1:
            md_link = get_report_download_link(report_content, "md")
            if md_link:
                st.markdown(md_link, unsafe_allow_html=True)
        with col_rep2:
            html_link = get_report_download_link(report_content, "html")
            if html_link:
                st.markdown(html_link, unsafe_allow_html=True)
        with col_rep3:
            pdf_link = get_report_download_link(report_content, "pdf")
            if pdf_link:
                st.markdown(pdf_link, unsafe_allow_html=True)

        st.markdown("---")
        with st.expander("👁️ Preview Full Generated Report Text", expanded=False):
            st.markdown(report_content)

else:
    st.info("👆 Click **'Run Autonomous Engine'** above to trigger the deep problem-solving analysis pipeline.")