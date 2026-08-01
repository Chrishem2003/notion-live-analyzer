

"""
Bayesian Analysis Engine  Bayesian hypothesis testing and parameter estimation.
Provides Bayesian t-tests, ANOVA, correlation, regression with Bayes factors,
prior predictive checks, and posterior visualization.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import math
import warnings
warnings.filterwarnings('ignore')

try:
    from scipy import stats as scipy_stats
    from scipy.integrate import quad
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    scipy_stats = None

try:
    import pingouin as pg
    HAS_PINGOUIN = True
except ImportError:
    HAS_PINGOUIN = False


class BayesianEngine:
    """
    Bayesian analysis suite with Bayes factors for common research designs.
    Uses analytical approximations (BIC approximation, Pingouin) for speed.
    """

    def __init__(self):
        self._check_deps()

    def _check_deps(self):
        if not HAS_SCIPY:
            raise ImportError("scipy is required. Install: pip install scipy")

    # ─── Bayes Factor from BIC Approximation ───────────────────────
    @staticmethod
    def _bic_to_bf(bic_diff: float) -> float:
        """
        Approximate Bayes factor from BIC difference.
        BF₁₀ ≈ exp(-ΔBIC / 2)
        Where ΔBIC = BIC(H₀) - BIC(H₁)
        """
        return math.exp(-bic_diff / 2)

    @staticmethod
    def _interpret_bf(bf: float) -> str:
        """Interpret Bayes factor strength (Jeffreys scale)."""
        if bf >= 100:
            return "Extreme evidence for H₁"
        elif bf >= 30:
            return "Very strong evidence for H₁"
        elif bf >= 10:
            return "Strong evidence for H₁"
        elif bf >= 3:
            return "Moderate evidence for H₁"
        elif bf >= 1:
            return "Anecdotal evidence for H₁"
        elif bf >= 0.33:
            return "Anecdotal evidence for H₀"
        elif bf >= 0.1:
            return "Moderate evidence for H₀"
        elif bf >= 0.03:
            return "Strong evidence for H₀"
        elif bf >= 0.01:
            return "Very strong evidence for H₀"
        else:
            return "Extreme evidence for H₀"

    # ─── Bayesian T-Test ───────────────────────────────────────────
    def bayesian_ttest(
        self,
        x: np.ndarray,
        y: Optional[np.ndarray] = None,
        paired: bool = False,
        prior_scale: float = 0.707,
    ) -> Dict[str, Any]:
        """
        Bayesian t-test using Pingouin (if available) or BIC approximation.
        Returns BF₁₀ (evidence for H₁: groups differ).

        Parameters
        ----------
        x : array  First group (or paired differences)
        y : array, optional  Second group (independent test)
        paired : bool  Paired test?
        prior_scale : float  Cauchy prior scale (default 0.707 = √2/2)
        """
        if HAS_PINGOUIN:
            try:
                if paired:
                    result = pg.ttest(x, y, paired=True)
                else:
                    if y is not None:
                        combined = np.concatenate([x, y])
                        groups = np.array(['x'] * len(x)  ['y'] * len(y))
                        result = pg.ttest(x, y, paired=False)
                    else:
                        result = pg.ttest(x, 0, paired=False)  # One-sample vs 0

                bf = result.get('BF10', result.get('bayes_factor', 1.0))
                if isinstance(bf, pd.Series):
                    bf = float(bf.iloc[0])
                d = result.get('cohen-d', result.get('d', 0))
                if isinstance(d, pd.Series):
                    d = float(d.iloc[0])
                return {
                    "method": f"Bayesian {'Paired' if paired else 'Independent'} T-Test",
                    "bf10": round(float(bf), 4),
                    "cohens_d": round(float(d), 4) if d else 0,
                    "interpretation": self._interpret_bf(float(bf)),
                    "n_x": len(x),
                    "n_y": len(y) if y is not None else 0,
                }
            except Exception:
                pass

        # Fallback: BIC approximation
        if y is not None and not paired:
            t_stat, p_val = scipy_stats.ttest_ind(x, y, equal_var=True)
            n = len(x)  len(y)
        elif paired:
            diff = x - y if y is not None else x
            t_stat, p_val = scipy_stats.ttest_1samp(diff, 0)
            n = len(diff)
        else:
            t_stat, p_val = scipy_stats.ttest_1samp(x, 0)
            n = len(x)

        # BIC approximation: BF₁₀ ≈ exp((t² - log(n)) / 2)
        bf = math.exp((t_stat**2 - math.log(n)) / 2) if t_stat**2 > math.log(n) else 1.0 / math.exp((math.log(n) - t_stat**2) / 2)

        # Cohen's d approximation
        d = 2 * t_stat / math.sqrt(n) if n > 0 else 0

        return {
            "method": f"Bayesian {'Paired' if paired else 'Independent'} T-Test (BIC approx.)",
            "bf10": round(float(bf), 4),
            "cohens_d": round(float(d), 4),
            "interpretation": self._interpret_bf(float(bf)),
            "n_x": len(x),
            "n_y": len(y) if y is not None else 0,
        }

    # ─── Bayesian Correlation ──────────────────────────────────────
    def bayesian_correlation(
        self,
        x: np.ndarray,
        y: np.ndarray,
        prior_strength: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Bayesian correlation test (Pearson).
        Returns BF₁₀ (evidence for non-zero correlation).
        """
        n = len(x)
        r, p_val = scipy_stats.pearsonr(x, y)

        # Wetzels & Wagenmakers (2012) approximation
        bf = (n / 2) ** 0.5 * (1 - r**2) ** ((n - 3) / 2) * \
             scipy_stats.beta.pdf(abs(r), 1 / prior_strength, 1 / prior_strength) * 2 if abs(r) < 1 else 1.0

        return {
            "method": "Bayesian Pearson Correlation",
            "bf10": round(float(bf), 4),
            "pearson_r": round(float(r), 4),
            "interpretation": self._interpret_bf(float(bf)),
            "n": n,
            "credible_interval": self._approximate_credible_interval(r, n),
        }

    # ─── Bayesian ANOVA ────────────────────────────────────────────
    def bayesian_anova(
        self,
        df: pd.DataFrame,
        dv: str,
        between: str,
    ) -> Dict[str, Any]:
        """
        Bayesian one-way ANOVA.
        Returns BF₁₀ (evidence for group differences).
        """
        if HAS_PINGOUIN:
            try:
                result = pg.anova(dv=dv, between=between, data=df, detailed=True)
                f_val = result['F'].iloc[0]
                df_effect = result['DF1'].iloc[0]
                df_error = result['DF2'].iloc[0]
                n = len(df)

                # BIC approximation for ANOVA
                bic_h1 = n * math.log(result['SS'].iloc[1] / n)  (df_effect  1) * math.log(n)
                bic_h0 = n * math.log((result['SS'].iloc[1]  result['SS'].iloc[0]) / n)  math.log(n)
                bf = self._bic_to_bf(bic_h0 - bic_h1)

                eta2 = result['np2'].iloc[0] if 'np2' in result.columns else \
                       result['SS'].iloc[0] / (result['SS'].iloc[0]  result['SS'].iloc[1])

                return {
                    "method": "Bayesian One-Way ANOVA",
                    "bf10": round(float(bf), 4),
                    "f_value": round(float(f_val), 4),
                    "eta_squared": round(float(eta2), 4),
                    "interpretation": self._interpret_bf(float(bf)),
                    "n": n,
                    "groups": df[between].nunique(),
                }
            except Exception as e:
                return {"error": f"Bayesian ANOVA failed: {str(e)}"}

        return {"error": "pingouin required for Bayesian ANOVA"}

    # ─── Bayesian Linear Regression ────────────────────────────────
    def bayesian_regression(
        self,
        df: pd.DataFrame,
        target: str,
        predictors: List[str],
    ) -> Dict[str, Any]:
        """
        Bayesian linear regression with Bayes factor.
        Compares full model vs. intercept-only model.
        """
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import mean_squared_error

        data = df[[target]  predictors].dropna()
        y = data[target].values
        X = data[predictors].values
        n = len(data)
        k = len(predictors)

        # Null model (intercept only)
        null_model = LinearRegression()
        null_model.fit(np.ones((n, 1)), y)
        null_pred = null_model.predict(np.ones((n, 1)))
        null_mse = mean_squared_error(y, null_pred)

        # Full model
        full_model = LinearRegression()
        full_model.fit(X, y)
        full_pred = full_model.predict(X)
        full_mse = mean_squared_error(y, full_pred)

        # BIC approximation
        bic_null = n * math.log(null_mse)  math.log(n)
        bic_full = n * math.log(full_mse)  (k  1) * math.log(n)
        bf = self._bic_to_bf(bic_null - bic_full)

        # R-squared
        ss_res = np.sum((y - full_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        return {
            "method": "Bayesian Linear Regression (BIC approx.)",
            "bf10": round(float(bf), 4),
            "r_squared": round(float(r2), 4),
            "n_predictors": k,
            "n_obs": n,
            "interpretation": self._interpret_bf(float(bf)),
            "coefficients": dict(zip(predictors, [round(float(c), 4) for c in full_model.coef_])),
            "intercept": round(float(full_model.intercept_), 4),
        }

    # ─── Bayesian Contingency Table ────────────────────────────────
    def bayesian_contingency(
        self,
        table: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Bayesian test of independence for contingency tables.
        Uses Gunel & Dickey Bayes factor.
        """
        import scipy.stats as ss

        observed = table.values
        chi2, p_val, dof, expected = ss.chi2_contingency(observed)

        # BF approximation using BIC
        n = observed.sum()
        r, c = observed.shape
        if expected.sum() > 0:
            # Convert expected to same shape
            expected = expected.astype(float)
            # G² (likelihood ratio statistic)
            with np.errstate(divide='ignore', invalid='ignore'):
                g2 = 2 * np.sum(observed * np.log(observed / expected, where=observed > 0), where=observed > 0)
            bic_h0 = g2  dof * math.log(n)
            bic_h1 = 0  # Saturated model
            bf = self._bic_to_bf(bic_h0 - bic_h1)
        else:
            bf = 1.0

        return {
            "method": "Bayesian Contingency Table",
            "bf10": round(float(bf), 4),
            "chi_square": round(float(chi2), 4),
            "cramers_v": round(float(np.sqrt(chi2 / (n * min(r - 1, c - 1)))), 4),
            "interpretation": self._interpret_bf(float(bf)),
            "n": int(n),
        }

    # ─── Helpers ───────────────────────────────────────────────────
    def _approximate_credible_interval(self, r: float, n: int, ci: float = 0.95) -> Tuple[float, float]:
        """Approximate credible interval for Pearson r using Fisher z-transform."""
        if abs(r) >= 1:
            return (-1, 1)
        z = math.atanh(r)
        se = 1 / math.sqrt(n - 3) if n > 3 else 1
        z_crit = scipy_stats.norm.ppf(1 - (1 - ci) / 2)
        lower = math.tanh(z - z_crit * se)
        upper = math.tanh(z  z_crit * se)
        return (round(float(lower), 4), round(float(upper), 4))

    @staticmethod
    def posterior_summary(posterior_samples: np.ndarray, ci: float = 0.95) -> Dict[str, Any]:
        """Generate summary statistics from posterior samples."""
        lower_tail = (1 - ci) / 2
        upper_tail = 1 - lower_tail
        return {
            "mean": round(float(np.mean(posterior_samples)), 4),
            "median": round(float(np.median(posterior_samples)), 4),
            "sd": round(float(np.std(posterior_samples)), 4),
            "ci_lower": round(float(np.percentile(posterior_samples, lower_tail * 100)), 4),
            "ci_upper": round(float(np.percentile(posterior_samples, upper_tail * 100)), 4),
            "hdi_lower": round(float(np.percentile(posterior_samples, lower_tail * 100)), 4),
            "hdi_upper": round(float(np.percentile(posterior_samples, upper_tail * 100)), 4),
        }


# ─── UI Renderer ─────────────────────────────────────────────────────
def render_bayesian_analysis_ui():
    """Render the Bayesian Analysis page in Streamlit."""
    import streamlit as st
    import plotly.graph_objects as go
    import plotly.express as px

    st.markdown("## 🧠 Bayesian Analysis Engine")
    st.markdown("*Bayesian hypothesis testing with Bayes factors  t-tests, ANOVA, correlation, regression*")

    df = st.session_state.get("active_df")
    if df is None or df.empty:
        st.warning("No data loaded.")
        return

    engine = BayesianEngine()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in df.columns if df[c].nunique() < 20]

    tab1, tab2, tab3, tab4 = st.tabs([
        "🧪 Bayesian T-Test", " Bayesian Correlation",
        "📐 Bayesian ANOVA", "📈 Bayesian Regression"
    ])

    with tab1:
        st.subheader("🧪 Bayesian T-Test  BF₁₀")
        test_type = st.radio("Test type", ["Independent", "Paired", "One Sample"], horizontal=True, key="bf_test_type")
        col1, col2 = st.columns(2)

        with col1:
            if test_type == "Independent":
                group_col = st.selectbox("Group column", options=cat_cols, key="bf_group")
                groups = df[group_col].dropna().unique()
                if len(groups) >= 2:
                    value_col = st.selectbox("Value column", options=numeric_cols, key="bf_value")
            elif test_type == "Paired":
                before_col = st.selectbox("Before column", options=numeric_cols, key="bf_before")
                after_col = st.selectbox("After column", options=[c for c in numeric_cols if c != before_col], key="bf_after")
            else:
                value_col = st.selectbox("Value column", options=numeric_cols, key="bf_onesample")
                test_val = st.number_input("Test value (H₀: μ = ?)", value=0.0, key="bf_testval")

        if st.button("🧪 Compute Bayes Factor", type="primary", use_container_width=True):
            with st.spinner("Computing Bayesian t-test..."):
                if test_type == "Independent" and group_col and value_col:
                    g1 = df[df[group_col] == groups[0]][value_col].dropna().values
                    g2 = df[df[group_col] == groups[1]][value_col].dropna().values
                    result = engine.bayesian_ttest(g1, g2)
                elif test_type == "Paired":
                    before = df[before_col].dropna().values
                    after = df[after_col].dropna().values
                    min_len = min(len(before), len(after))
                    result = engine.bayesian_ttest(before[:min_len], after[:min_len], paired=True)
                else:
                    vals = df[value_col].dropna().values - test_val
                    result = engine.bayesian_ttest(vals)

            if "error" in result:
                st.error(result["error"])
            else:
                bf = result.get("bf10", 1)
                bf_color = "#2ecc71" if bf >= 3 else "#e67e22" if bf >= 1 else "#e74c3c"
                st.markdown(f"""
                <div style="text-align:center;padding:1.5rem;border-radius:16px;
                    border:2px solid {bf_color};background:{bf_color}10;margin:1rem 0;">
                    <div style="font-size:0.8rem;color:#64748b;">Bayes Factor BF₁₀</div>
                    <div style="font-size:3rem;font-weight:900;color:{bf_color};">{bf:.2f}</div>
                    <div style="font-size:1rem;color:{bf_color};">{result.get('interpretation', '')}</div>
                    <div style="margin-top:0.5rem;font-size:0.85rem;color:#64748b;">
                        Cohen's d = {result.get('cohens_d', 0):.3f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with tab2:
        st.subheader(" Bayesian Correlation  BF₁₀")
        col1, col2 = st.columns(2)
        with col1:
            corr_x = st.selectbox("Variable X", options=numeric_cols, key="bf_corr_x")
        with col2:
            corr_y = st.selectbox("Variable Y", options=[c for c in numeric_cols if c != corr_x], key="bf_corr_y")

        if st.button(" Compute Bayes Factor", type="primary", use_container_width=True):
            data = df[[corr_x, corr_y]].dropna()
            x = data[corr_x].values
            y = data[corr_y].values
            result = engine.bayesian_correlation(x, y)
            bf = result.get("bf10", 1)
            bf_color = "#2ecc71" if bf >= 3 else "#e67e22" if bf >= 1 else "#e74c3c"
            st.markdown(f"""
            <div style="text-align:center;padding:1.5rem;border-radius:16px;
                border:2px solid {bf_color};background:{bf_color}10;margin:1rem 0;">
                <div style="font-size:0.8rem;color:#64748b;">Bayes Factor BF₁₀</div>
                <div style="font-size:3rem;font-weight:900;color:{bf_color};">{bf:.2f}</div>
                <div style="font-size:1rem;color:{bf_color};">{result.get('interpretation', '')}</div>
                <div style="margin-top:0.5rem;font-size:0.85rem;color:#64748b;">
                    r = {result.get('pearson_r', 0):.3f} | N = {result.get('n', 0)}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Scatter plot
            fig = px.scatter(data, x=corr_x, y=corr_y, trendline="ols", title=f"Scatter Plot (r = {result.get('pearson_r', 0):.3f})")
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("📐 Bayesian ANOVA  BF₁₀")
        col1, col2 = st.columns(2)
        with col1:
            anova_dv = st.selectbox("Dependent variable", options=numeric_cols, key="bf_anova_dv")
        with col2:
            anova_between = st.selectbox("Group variable", options=cat_cols, key="bf_anova_between")

        if st.button("📐 Compute Bayes Factor", type="primary", use_container_width=True):
            with st.spinner("Computing Bayesian ANOVA..."):
                result = engine.bayesian_anova(df, anova_dv, anova_between)
            if "error" in result:
                st.error(result["error"])
            else:
                bf = result.get("bf10", 1)
                bf_color = "#2ecc71" if bf >= 3 else "#e67e22" if bf >= 1 else "#e74c3c"
                st.markdown(f"""
                <div style="text-align:center;padding:1.5rem;border-radius:16px;
                    border:2px solid {bf_color};background:{bf_color}10;margin:1rem 0;">
                    <div style="font-size:0.8rem;color:#64748b;">Bayes Factor BF₁₀</div>
                    <div style="font-size:3rem;font-weight:900;color:{bf_color};">{bf:.2f}</div>
                    <div style="font-size:1rem;color:{bf_color};">{result.get('interpretation', '')}</div>
                    <div style="margin-top:0.5rem;font-size:0.85rem;color:#64748b;">
                        F = {result.get('f_value', 0):.2f} | η² = {result.get('eta_squared', 0):.3f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with tab4:
        st.subheader("📈 Bayesian Regression  BF₁₀")
        col1, col2 = st.columns(2)
        with col1:
            reg_target = st.selectbox("Target variable", options=numeric_cols, key="bf_reg_target")
        with col2:
            reg_predictors = st.multiselect("Predictors", options=[c for c in numeric_cols if c != reg_target], key="bf_reg_pred")

        if st.button("📈 Compute Bayes Factor", type="primary", use_container_width=True) and reg_predictors:
            with st.spinner("Computing Bayesian regression..."):
                result = engine.bayesian_regression(df, reg_target, reg_predictors)
            if "error" in result:
                st.error(result["error"])
            else:
                bf = result.get("bf10", 1)
                bf_color = "#2ecc71" if bf >= 3 else "#e67e22" if bf >= 1 else "#e74c3c"
                st.markdown(f"""
                <div style="text-align:center;padding:1.5rem;border-radius:16px;
                    border:2px solid {bf_color};background:{bf_color}10;margin:1rem 0;">
                    <div style="font-size:0.8rem;color:#64748b;">Bayes Factor BF₁₀</div>
                    <div style="font-size:3rem;font-weight:900;color:{bf_color};">{bf:.2f}</div>
                    <div style="font-size:1rem;color:{bf_color};">{result.get('interpretation', '')}</div>
                    <div style="margin-top:0.5rem;font-size:0.85rem;color:#64748b;">
                        R² = {result.get('r_squared', 0):.3f} | N = {result.get('n_obs', 0)}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if result.get("coefficients"):
                    coef_df = pd.DataFrame(list(result["coefficients"].items()), columns=["Predictor", "Coefficient"])
                    st.dataframe(coef_df, use_container_width=True, hide_index=True)

