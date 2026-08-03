
"""
Advanced Resampling & Validation  Bootstrap confidence intervals, permutation tests,
cross-validation, Monte Carlo simulations.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple, Callable
import pandas as pd
import numpy as np
import math
import warnings
warnings.filterwarnings('ignore')

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from sklearn.model_selection import KFold, StratifiedKFold, LeaveOneOut, TimeSeriesSplit
    from sklearn.metrics import accuracy_score, r2_score, mean_squared_error
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class ResamplingEngine:
    """Advanced resampling methods for robust inference."""

    @staticmethod
    def bootstrap_ci(
        data: np.ndarray,
        statistic: Callable = np.mean,
        n_bootstrap: int = 1000,
        ci_level: float = 0.95,
        method: str = "percentile",
    ) -> Dict[str, Any]:
        """
        Compute bootstrap confidence intervals for a statistic.
        """
        n = len(data)
        bootstrap_stats = []
        rng = np.random.RandomState(42)

        for _ in range(n_bootstrap):
            sample = rng.choice(data, size=n, replace=True)
            bootstrap_stats.append(statistic(sample))

        bootstrap_stats = np.array(bootstrap_stats)
        alpha = 1 - ci_level

        if method == "percentile":
            ci_lower = np.percentile(bootstrap_stats, alpha / 2 * 100)
            ci_upper = np.percentile(bootstrap_stats, (1 - alpha / 2) * 100)
        elif method == "bca":
            # Bias-corrected and accelerated (simplified)
            z0 = scipy_stats.norm.ppf(np.mean(bootstrap_stats < statistic(data)))
            jackknife = np.array([statistic(np.delete(data, i)) for i in range(n)])
            jack_std = np.std(jackknife)
            if jack_std > 0:
                acc = np.sum((np.mean(jackknife) - jackknife)**3) / (6 * np.sum((np.mean(jackknife) - jackknife)**2)**1.5)
            else:
                acc = 0
            a1 = scipy_stats.norm.cdf(z0  (z0  scipy_stats.norm.ppf(alpha / 2)) / (1 - acc * (z0  scipy_stats.norm.ppf(alpha / 2))))
            a2 = scipy_stats.norm.cdf(z0  (z0  scipy_stats.norm.ppf(1 - alpha / 2)) / (1 - acc * (z0  scipy_stats.norm.ppf(1 - alpha / 2))))
            ci_lower = np.percentile(bootstrap_stats, a1 * 100)
            ci_upper = np.percentile(bootstrap_stats, a2 * 100)
        elif method == "basic":
            se = np.std(bootstrap_stats)
            z = scipy_stats.norm.ppf(1 - alpha / 2)
            point_est = statistic(data)
            ci_lower = point_est - z * se
            ci_upper = point_est  z * se
        else:
            ci_lower = np.percentile(bootstrap_stats, alpha / 2 * 100)
            ci_upper = np.percentile(bootstrap_stats, (1 - alpha / 2) * 100)

        return {
            "method": f"Bootstrap (n={n_bootstrap}, {method})",
            "statistic": statistic.__name__ if hasattr(statistic, '__name__') else "custom",
            "point_estimate": round(float(statistic(data)), 4),
            "ci_lower": round(float(ci_lower), 4),
            "ci_upper": round(float(ci_upper), 4),
            "ci_level": ci_level,
            "bootstrap_se": round(float(np.std(bootstrap_stats)), 4),
            "bias": round(float(np.mean(bootstrap_stats) - statistic(data)), 4),
            "n_bootstrap": n_bootstrap,
        }

    @staticmethod
    def permutation_test(
        group1: np.ndarray,
        group2: np.ndarray,
        statistic: Callable = lambda a, b: np.mean(a) - np.mean(b),
        n_permutations: int = 5000,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """
        Non-parametric permutation test for comparing two groups.
        """
        observed = statistic(group1, group2)
        combined = np.concatenate([group1, group2])
        n1 = len(group1)
        permuted_stats = []
        rng = np.random.RandomState(42)

        for _ in range(n_permutations):
            rng.shuffle(combined)
            perm_group1 = combined[:n1]
            perm_group2 = combined[n1:]
            permuted_stats.append(statistic(perm_group1, perm_group2))

        permuted_stats = np.array(permuted_stats)

        if alternative == "two-sided":
            p_value = np.mean(np.abs(permuted_stats) >= np.abs(observed))
        elif alternative == "greater":
            p_value = np.mean(permuted_stats >= observed)
        elif alternative == "less":
            p_value = np.mean(permuted_stats <= observed)
        else:
            p_value = np.mean(np.abs(permuted_stats) >= np.abs(observed))

        return {
            "method": "Permutation Test",
            "n_permutations": n_permutations,
            "observed_statistic": round(float(observed), 4),
            "p_value": round(float(p_value), 4),
            "significant": p_value < 0.05,
            "alternative": alternative,
            "permutation_ci": [round(float(np.percentile(permuted_stats, 2.5)), 4),
                               round(float(np.percentile(permuted_stats, 97.5)), 4)],
        }

    @staticmethod
    def cross_validate(
        X: np.ndarray,
        y: np.ndarray,
        model: Any,
        n_folds: int = 5,
        stratified: bool = False,
        scoring: str = "accuracy",
    ) -> Dict[str, Any]:
        """
        Perform k-fold cross-validation.
        """
        if not HAS_SKLEARN:
            return {"error": "scikit-learn required"}

        if stratified:
            cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
        else:
            cv = KFold(n_splits=n_folds, shuffle=True, random_state=42)

        scores = []
        for train_idx, test_idx in cv.split(X, y):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            if scoring == "accuracy":
                score = accuracy_score(y_test, y_pred)
            elif scoring == "r2":
                score = r2_score(y_test, y_pred)
            elif scoring == "mse":
                score = -mean_squared_error(y_test, y_pred)
            else:
                score = accuracy_score(y_test, y_pred)
            scores.append(score)

        return {
            "method": f"{n_folds}-Fold Cross-Validation",
            "n_folds": n_folds,
            "scoring": scoring,
            "scores": [round(float(s), 4) for s in scores],
            "mean_score": round(float(np.mean(scores)), 4),
            "std_score": round(float(np.std(scores)), 4),
            "ci_lower": round(float(np.mean(scores) - 1.96 * np.std(scores) / np.sqrt(n_folds)), 4),
            "ci_upper": round(float(np.mean(scores)  1.96 * np.std(scores) / np.sqrt(n_folds)), 4),
        }

    @staticmethod
    def monte_carlo_power(
        effect_size: float,
        sample_size: int,
        n_simulations: int = 1000,
        alpha: float = 0.05,
        test_type: str = "ttest",
    ) -> Dict[str, Any]:
        """
        Estimate statistical power via Monte Carlo simulation.
        """
        if not HAS_SCIPY:
            return {"error": "scipy required"}

        significant = 0
        rng = np.random.RandomState(42)

        for _ in range(n_simulations):
            if test_type == "ttest":
                group1 = rng.normal(0, 1, size=sample_size)
                group2 = rng.normal(effect_size, 1, size=sample_size)
                _, p = scipy_stats.ttest_ind(group1, group2)
            elif test_type == "correlation":
                x = rng.normal(0, 1, size=sample_size)
                y = effect_size * x  np.sqrt(1 - effect_size**2) * rng.normal(0, 1, size=sample_size)
                _, p = scipy_stats.pearsonr(x, y)
            else:
                group1 = rng.normal(0, 1, size=sample_size)
                group2 = rng.normal(effect_size, 1, size=sample_size)
                _, p = scipy_stats.ttest_ind(group1, group2)

            if p < alpha:
                significant = 1

        power = significant / n_simulations

        return {
            "method": "Monte Carlo Power Analysis",
            "effect_size": effect_size,
            "sample_size": sample_size,
            "n_simulations": n_simulations,
            "alpha": alpha,
            "estimated_power": round(float(power), 4),
            "interpretation": "Adequate" if power >= 0.8 else "Low",
        }

    @staticmethod
    def bootstrap_hypothesis_test(
        group1: np.ndarray,
        group2: np.ndarray,
        n_bootstrap: int = 5000,
    ) -> Dict[str, Any]:
        """
        Bootstrap-based two-sample hypothesis test (no parametric assumptions).
        """
        observed_diff = np.mean(group1) - np.mean(group2)
        combined = np.concatenate([group1, group2])
        n1, n2 = len(group1), len(group2)
        rng = np.random.RandomState(42)
        bootstrap_diffs = []

        for _ in range(n_bootstrap):
            sample = rng.choice(combined, size=n1  n2, replace=True)
            b1 = sample[:n1]
            b2 = sample[n1:]
            bootstrap_diffs.append(np.mean(b1) - np.mean(b2))

        bootstrap_diffs = np.array(bootstrap_diffs)
        p_value = 2 * min(np.mean(bootstrap_diffs >= 0), np.mean(bootstrap_diffs <= 0))

        return {
            "method": "Bootstrap Hypothesis Test",
            "observed_difference": round(float(observed_diff), 4),
            "p_value": round(float(p_value), 4),
            "significant": p_value < 0.05,
            "n_bootstrap": n_bootstrap,
            "bootstrap_ci_diff": [round(float(np.percentile(bootstrap_diffs, 2.5)), 4),
                                  round(float(np.percentile(bootstrap_diffs, 97.5)), 4)],
        }


# â”€â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def render_resampling_ui():
    """Render the Resampling & Validation page."""
    import streamlit as st
    import plotly.express as px
    import plotly.graph_objects as go

    st.markdown("## ðŸ”„ Advanced Resampling & Validation")
    st.markdown("*Bootstrap, permutation tests, cross-validation, Monte Carlo simulations*")

    df = st.session_state.get("active_df")
    engine = ResamplingEngine()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "ðŸŽ² Bootstrap CI", "ðŸ”„ Permutation Test", " Cross-Validation",
        "âš¡ Monte Carlo Power", "ðŸ“ˆ Bootstrap Hypothesis Test"
    ])

    with tab1:
        st.subheader("ðŸŽ² Bootstrap Confidence Intervals")
        if df is not None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            col = st.selectbox("Variable", options=numeric_cols, key="bs_col")
            stat = st.selectbox("Statistic", options=["mean", "median", "std", "var"], key="bs_stat")
            n_boot = st.slider("Number of bootstrap samples", 100, 5000, 1000, key="bs_n")
            ci_method = st.selectbox("CI method", options=["percentile", "bca", "basic"], key="bs_method")
            if st.button("ðŸŽ² Compute Bootstrap CI", type="primary"):
                stat_map = {"mean": np.mean, "median": np.median, "std": np.std, "var": np.var}
                data = df[col].dropna().values
                result = engine.bootstrap_ci(data, stat_map[stat], n_boot, 0.95, ci_method)
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("Point Estimate", result["point_estimate"])
                with col2: st.metric("CI Lower", result["ci_lower"])
                with col3: st.metric("CI Upper", result["ci_upper"])
                st.info(f"Bootstrap SE = {result['bootstrap_se']:.4f}, Bias = {result['bias']:.4f}")
        else:
            st.warning("No data loaded.")

    with tab2:
        st.subheader("ðŸ”„ Permutation Test (Two-Group Comparison)")
        if df is not None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            cat_cols = [c for c in df.columns if df[c].nunique() == 2]
            if cat_cols and numeric_cols:
                group_col = st.selectbox("Group variable (2 groups)", options=cat_cols, key="perm_group")
                value_col = st.selectbox("Value variable", options=numeric_cols, key="perm_value")
                alt = st.selectbox("Alternative", options=["two-sided", "greater", "less"], key="perm_alt")
                if st.button("ðŸ”„ Run Permutation Test", type="primary"):
                    groups = df[group_col].dropna().unique()
                    g1 = df[df[group_col] == groups[0]][value_col].dropna().values
                    g2 = df[df[group_col] == groups[1]][value_col].dropna().values
                    result = engine.permutation_test(g1, g2, alternative=alt)
                    st.metric("Observed Difference", result["observed_statistic"])
                    st.metric("p-value", result["p_value"])
                    st.info(f"{'âœ… Significant' if result['significant'] else 'âŒ Not significant'} (p {'<' if result['p_value'] < 0.001 else '='} {result['p_value']:.4f})")
            else:
                st.warning("Need a binary categorical and a numeric variable.")
        else:
            st.warning("No data loaded.")

    with tab3:
        st.subheader(" Cross-Validation")
        st.info("Cross-validation requires scikit-learn. Load data and select features/target.")
        if df is not None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            target = st.selectbox("Target", options=numeric_cols, key="cv_target")
            features = st.multiselect("Features", options=[c for c in numeric_cols if c != target], key="cv_features")
            n_folds = st.slider("Number of folds", 2, 10, 5, key="cv_folds")
            if st.button(" Run CV", type="primary") and features and HAS_SKLEARN:
                from sklearn.linear_model import LinearRegression
                X = df[features].fillna(0).values
                y = df[target].fillna(0).values
                model = LinearRegression()
                result = engine.cross_validate(X, y, model, n_folds, scoring="r2")
                st.metric("Mean RÂ²", result["mean_score"])
                st.metric("Std RÂ²", result["std_score"])
                st.info(f"95% CI: [{result['ci_lower']:.4f}, {result['ci_upper']:.4f}]")
        else:
            st.warning("No data loaded.")

    with tab4:
        st.subheader("âš¡ Monte Carlo Power Analysis")
        es = st.number_input("Effect size (Cohen's d / correlation r)", value=0.5, step=0.05, key="mc_es")
        n = st.number_input("Sample size per group", value=50, step=5, key="mc_n")
        n_sim = st.slider("Number of simulations", 100, 5000, 1000, key="mc_sim")
        test = st.selectbox("Test type", options=["ttest", "correlation"], key="mc_test")
        if st.button("âš¡ Estimate Power", type="primary"):
            result = engine.monte_carlo_power(es, int(n), n_sim, 0.05, test)
            st.metric("Estimated Power", f"{result['estimated_power']:.3f}")
            st.info(f"Power = {result['estimated_power']:.2%}  {result['interpretation']}")

    with tab5:
        st.subheader("ðŸ“ˆ Bootstrap Hypothesis Test")
        if df is not None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            cat_cols = [c for c in df.columns if df[c].nunique() == 2]
            if cat_cols and numeric_cols:
                bg_col = st.selectbox("Group variable", options=cat_cols, key="bht_group")
                bv_col = st.selectbox("Value variable", options=numeric_cols, key="bht_value")
                if st.button("ðŸ“ˆ Run Bootstrap Test", type="primary"):
                    groups = df[bg_col].dropna().unique()
                    g1 = df[df[bg_col] == groups[0]][bv_col].dropna().values
                    g2 = df[df[bg_col] == groups[1]][bv_col].dropna().values
                    result = engine.bootstrap_hypothesis_test(g1, g2)
                    st.metric("Observed Difference", result["observed_difference"])
                    st.metric("p-value", result["p_value"])
                    st.info(f"95% CI of difference: [{result['bootstrap_ci_diff'][0]:.4f}, {result['bootstrap_ci_diff'][1]:.4f}]")
            else:
                st.warning("Need a binary categorical and a numeric variable.")
        else:
            st.warning("No data loaded.")
