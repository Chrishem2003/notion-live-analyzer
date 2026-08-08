"""
Page 59 — SPSS-Grade Advanced Statistical Suite
"""
import sys
from pathlib import Path

import streamlit as st

current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

st.set_page_config(page_title="SPSS Advanced Suite", page_icon="📊", layout="wide")

import pandas as pd  # noqa: E402


def _hero(title, subtitle, badge):
    st.markdown(
        f"""
        <div style="padding:1.6rem;background:linear-gradient(135deg,rgba(168,85,247,.12),rgba(11,19,33,.96));border-radius:14px;border:1px solid rgba(168,85,247,.35);margin-bottom:1.2rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;">
                <h1 style="color:#a855f7 !important;font-size:1.9rem;margin:0;font-weight:800;">{title}</h1>
                <span style="background:rgba(168,85,247,.15);color:#a855f7;padding:.3rem .8rem;border-radius:999px;font-size:.75rem;font-weight:700;border:1px solid #a855f7;">{badge}</span>
            </div>
            <p style="color:#cbd5e1 !important;margin:.4rem 0 0;font-size:.95rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


_hero(
    "📊 SPSS-Grade Advanced Statistical Suite",
    "Run advanced procedures beyond base SPSS: ANCOVA, MANOVA, survey weighting, factor retention (KMO/Bartlett/eigenvalues), bootstrapped confidence intervals, and export to native SPSS .sav files.",
    "SPSS • STATA • SAS Replacement",
)

# Load the active dataframe from session state (shared across pages)
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    np.random.seed(42)
    active_df = pd.DataFrame({
        "Group": np.random.choice(["A", "B", "C"], 120),
        "Score": np.random.normal(70, 12, 120),
        "Covariate": np.random.normal(50, 8, 120),
        "Outcome": np.random.normal(5, 1.5, 120),
        "Biomarker": np.random.normal(100, 15, 120),
    })
    st.info("No active dataset found — using a sample dataset. Upload data in the File Analyzer page and share it across pages.")

try:
    from modules.spss_suite import SPSSSuite

    suite = SPSSSuite()
except Exception as e:
    st.error(f"Failed to load SPSS suite: {e}")
    st.stop()

numeric_cols = active_df.select_dtypes(include=["number"]).columns.tolist()
cat_cols = active_df.select_dtypes(include=["object", "category"]).columns.tolist()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📐 ANCOVA",
    "🧮 MANOVA",
    "⚖️ Survey Weighting",
    "🧠 Factor Retention",
    "🎲 Bootstrap & .sav Export",
])

with tab1:
    st.markdown("#### Analysis of Covariance (ANCOVA)")
    if numeric_cols and cat_cols:
        vg = st.selectbox("Dependent variable", numeric_cols, key="ancova_value")
        gg = st.selectbox("Grouping factor", cat_cols, key="ancova_group")
        cg = st.selectbox("Covariate", [c for c in numeric_cols if c != vg], key="ancova_cov")
        if st.button("Run ANCOVA", type="primary"):
            res = suite.ancova(active_df, gg, vg, cg)
            if "error" in res:
                st.error(res["error"])
            else:
                st.success(f"R² = {res['r_squared']} | Group p-value = {res['p_value_group']}")
                st.dataframe(res["anova_table"], use_container_width=True)
    else:
        st.warning("Need at least one numeric and one categorical column.")

with tab2:
    st.markdown("#### Multivariate ANOVA (MANOVA)")
    if numeric_cols and cat_cols:
        deps = st.multiselect("Dependent variables", numeric_cols, default=numeric_cols[:2])
        gg = st.selectbox("Grouping factor", cat_cols, key="manova_group")
        if len(deps) >= 2 and st.button("Run MANOVA", type="primary"):
            res = suite.manova(active_df, gg, deps)
            if "error" in res:
                st.error(res["error"])
            else:
                st.dataframe(res["summary"], use_container_width=True)
    else:
        st.warning("Need at least 2 numeric and 1 categorical column.")

with tab3:
    st.markdown("#### Post-Stratification Survey Weighting")
    if cat_cols:
        gg = st.selectbox("Stratum / category", cat_cols, key="weight_cat")
        cats = active_df[gg].dropna().unique().tolist()
        st.caption("Enter population totals for each category:")
        totals = {}
        for i, c in enumerate(cats):
            totals[str(c)] = st.number_input(f"Population for '{c}'", value=1000.0, key=f"pop_{i}")
        if st.button("Apply Survey Weights", type="primary"):
            weighted = suite.survey_weight(active_df, gg, totals)
            st.session_state["active_df"] = weighted
            st.success("Survey weights computed and applied to active dataset.")
            st.dataframe(weighted[["survey_weight"]].head(20), use_container_width=True)
    else:
        st.warning("Need a categorical column for stratification.")

with tab4:
    st.markdown("#### Factor Retention Diagnostics (KMO • Bartlett • Eigenvalues)")
    if numeric_cols:
        vars_sel = st.multiselect("Select variables", numeric_cols, default=numeric_cols[:4])
        if len(vars_sel) >= 2 and st.button("Run Factor Diagnostics", type="primary"):
            res = suite.factor_retention(active_df, vars_sel)
            if "error" in res:
                st.error(res["error"])
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("KMO", res["kmo_overall"])
                c2.metric("Bartlett p-value", res["bartlett_p"])
                c3.metric("Recommended Factors", res["recommended_factors"])
                st.markdown("**Eigenvalues:**")
                st.bar_chart(pd.Series(res["eigenvalues"]))
    else:
        st.warning("Need at least 2 numeric columns.")

with tab5:
    st.markdown("#### Bootstrap Confidence Intervals")
    if numeric_cols:
        col = st.selectbox("Variable to bootstrap", numeric_cols, key="boot_col")
        stat_fn = st.selectbox("Statistic", ["mean", "median", "std"])
        n_boot = st.slider("Bootstrap samples", 100, 5000, 1000, 100)
        if st.button("Run Bootstrap", type="primary"):
            res = suite.bootstrap_statistic(active_df, col, stat_fn, n_boot=n_boot)
            if "error" in res:
                st.error(res["error"])
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Statistic", res["statistic"])
                c2.metric("CI Lower", res["ci_lower"])
                c3.metric("CI Upper", res["ci_upper"])
    st.markdown("---")
    st.markdown("#### Export to SPSS .sav")
    if st.button("📥 Download Active Dataset as .sav", type="primary"):
        bytes_out = suite.export_sav(active_df)
        if bytes_out:
            st.download_button("⬇️ Download .sav", data=bytes_out, file_name="dataset.sav", mime="application/octet-stream", use_container_width=True)
        else:
            st.warning("pyreadstat not installed. Install with `pip install pyreadstat` to export .sav files.")

st.markdown("---")
st.caption("CHRISHEM Multi-Problem Solver • SPSS Advanced Suite")
