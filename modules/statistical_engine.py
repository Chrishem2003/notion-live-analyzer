
"""
Statistical Engine  SPSS-level statistical analysis suite.
Replaces SPSS, STATA, and SAS for common research analyses.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

# ─── Graceful Import of scipy ────────────────────────────────────────
try:
    from scipy import stats as scipy_stats
    from scipy.stats import (
        ttest_ind, ttest_rel, ttest_1samp,
        f_oneway, chi2_contingency, pearsonr, spearmanr,
        kruskal, mannwhitneyu, wilcoxon, friedmanchisquare,
        shapiro, normaltest, kstest,
    )
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    scipy_stats = None
    # Placeholder assignments to avoid NameError during class definition
    ttest_ind = ttest_rel = ttest_1samp = None
    f_oneway = chi2_contingency = pearsonr = spearmanr = None
    kruskal = mannwhitneyu = wilcoxon = friedmanchisquare = None
    shapiro = normaltest = kstest = None

# ─── Graceful Import of statsmodels ──────────────────────────────────
try:
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    from statsmodels.stats.power import TTestIndPower, TTestPower
    from statsmodels.stats.proportion import proportions_ztest
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    pairwise_tukeyhsd = None
    TTestIndPower = TTestPower = None
    proportions_ztest = None

# ─── Graceful Import of pingouin ─────────────────────────────────────
try:
    import pingouin as pg
    HAS_PINGOUIN = True
except ImportError:
    HAS_PINGOUIN = False
    pg = None

class StatisticalEngine:
    """Complete statistical analysis engine."""

    def __init__(self):
        """Initialize and check dependency availability."""
        self._has_scipy = HAS_SCIPY
        self._has_statsmodels = HAS_STATSMODELS
        self._has_pingouin = HAS_PINGOUIN

    def _require_scipy(self) -> Optional[str]:
        """Return error message if scipy is not available."""
        if not self._has_scipy:
            return ("scipy is not installed. Click Settings → Dependency Manager → 'Fix All Missing Packages' "
                    "to install it automatically, or run: pip install scipy")
        return None

    def _require_statsmodels(self) -> Optional[str]:
        """Return error message if statsmodels is not available."""
        if not self._has_statsmodels:
            return ("statsmodels is not installed. Click Settings → Dependency Manager → 'Fix All Missing Packages' "
                    "to install it automatically, or run: pip install statsmodels")
        return None

    def _require_pingouin(self) -> Optional[str]:
        """Return error message if pingouin is not available."""
        if not self._has_pingouin:
            return ("pingouin is not installed. Click Settings → Dependency Manager → 'Fix All Missing Packages' "
                    "to install it automatically, or run: pip install pingouin")
        return None

    # ─── DESCRIPTIVE STATISTICS ─────────────────────────────────────
    def descriptive_stats(self, df: pd.DataFrame, columns: List[str] = None) -> pd.DataFrame:
        """Compute comprehensive descriptive statistics."""
        if columns is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            columns = numeric_cols
        if not columns:
            return pd.DataFrame()

        results = []
        for col in columns:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            stats_dict = {
                "Variable": col,
                "N": len(series),
                "Missing": int(df[col].isna().sum()),
                "Mean": round(float(series.mean()), 4),
                "Median": round(float(series.median()), 4),
                "Mode": round(float(series.mode().iloc[0]), 4) if len(series.mode()) > 0 else None,
                "Std Dev": round(float(series.std()), 4),
                "Variance": round(float(series.var()), 4),
                "Skewness": round(float(series.skew()), 4),
                "Kurtosis": round(float(series.kurtosis()), 4),
                "Min": round(float(series.min()), 4),
                "Max": round(float(series.max()), 4),
                "Q1 (25%)": round(float(series.quantile(0.25)), 4),
                "Q3 (75%)": round(float(series.quantile(0.75)), 4),
                "IQR": round(float(series.quantile(0.75) - series.quantile(0.25)), 4),
                "Range": round(float(series.max() - series.min()), 4),
                "CV (%)": round(float(series.std() / series.mean() * 100), 4) if series.mean() != 0 else None,
            }
            results.append(stats_dict)
        return pd.DataFrame(results)

    # ─── FREQUENCY ANALYSIS ─────────────────────────────────────────
    def frequency_table(self, df: pd.DataFrame, col: str) -> pd.DataFrame:
        """Generate frequency table with percentages."""
        freq = df[col].value_counts(dropna=False).reset_index()
        freq.columns = [col, "Frequency"]
        freq["Percentage"] = round(freq["Frequency"] / len(df) * 100, 2)
        freq["Cumulative %"] = round(freq["Percentage"].cumsum(), 2)
        return freq

    def cross_tabulation(self, df: pd.DataFrame, row_col: str, col_col: str) -> pd.DataFrame:
        """Create a cross-tabulation (contingency table)."""
        cross = pd.crosstab(
            df[row_col], df[col_col],
            margins=True, margins_name="Total"
        )
        return cross

    # ─── T-TESTS ────────────────────────────────────────────────────
    def independent_ttest(self, df: pd.DataFrame, group_col: str, value_col: str) -> Dict[str, Any]:
        """Independent samples t-test with Cohen's d effect size."""
        err = self._require_scipy()
        if err:
            return {"error": err}
        groups = df[group_col].dropna().unique()
        if len(groups) != 2:
            return {"error": "Exactly 2 groups required for independent t-test"}
        group1 = df[df[group_col] == groups[0]][value_col].dropna()
        group2 = df[df[group_col] == groups[1]][value_col].dropna()
        if len(group1) < 2 or len(group2) < 2:
            return {"error": "Each group needs at least 2 observations"}
        t_stat, p_val = ttest_ind(group1, group2, equal_var=True)
        # Welch's t-test (unequal variance)
        t_stat_w, p_val_w = ttest_ind(group1, group2, equal_var=False)
        # Cohen's d
        n1, n2 = len(group1), len(group2)
        s1, s2 = group1.std(), group2.std()
        pooled_std = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
        cohens_d = (group1.mean() - group2.mean()) / pooled_std if pooled_std != 0 else 0
        return {
            "test": "Independent Samples T-Test",
            "group_1": str(groups[0]),
            "group_2": str(groups[1]),
            "n_1": n1,
            "n_2": n2,
            "mean_1": round(float(group1.mean()), 4),
            "mean_2": round(float(group2.mean()), 4),
            "mean_diff": round(float(group1.mean() - group2.mean()), 4),
            "t_statistic": round(float(t_stat), 4),
            "p_value": round(float(p_val), 4),
            "welch_t": round(float(t_stat_w), 4),
            "welch_p": round(float(p_val_w), 4),
            "cohens_d": round(float(cohens_d), 4),
            "significant": p_val < 0.05,
            "effect_size": "large" if abs(cohens_d) > 0.8 else "medium" if abs(cohens_d) > 0.5 else "small",
        }

    def paired_ttest(self, df: pd.DataFrame, before_col: str, after_col: str) -> Dict[str, Any]:
        """Paired samples t-test."""
        err = self._require_scipy()
        if err:
            return {"error": err}
        valid = df[[before_col, after_col]].dropna()
        if len(valid) < 3:
            return {"error": "Need at least 3 paired observations"}
        before, after = valid[before_col], valid[after_col]
        t_stat, p_val = ttest_rel(before, after)
        diff = after - before
        cohens_d = diff.mean() / diff.std() if diff.std() != 0 else 0
        return {
            "test": "Paired Samples T-Test",
            "n_pairs": len(valid),
            "mean_before": round(float(before.mean()), 4),
            "mean_after": round(float(after.mean()), 4),
            "mean_change": round(float(diff.mean()), 4),
            "t_statistic": round(float(t_stat), 4),
            "p_value": round(float(p_val), 4),
            "cohens_d": round(float(cohens_d), 4),
            "significant": p_val < 0.05,
        }

    def one_sample_ttest(self, df: pd.DataFrame, col: str, test_value: float = 0) -> Dict[str, Any]:
        """One-sample t-test against a population mean."""
        err = self._require_scipy()
        if err:
            return {"error": err}
        series = df[col].dropna()
        if len(series) < 3:
            return {"error": "Need at least 3 observations"}
        t_stat, p_val = ttest_1samp(series, test_value)
        cohens_d = (series.mean() - test_value) / series.std() if series.std() != 0 else 0
        return {
            "test": "One-Sample T-Test",
            "n": len(series),
            "mean": round(float(series.mean()), 4),
            "test_value": test_value,
            "mean_diff": round(float(series.mean() - test_value), 4),
            "t_statistic": round(float(t_stat), 4),
            "p_value": round(float(p_val), 4),
            "cohens_d": round(float(cohens_d), 4),
            "significant": p_val < 0.05,
        }

    # ─── ANOVA ──────────────────────────────────────────────────────
    def anova_one_way(self, df: pd.DataFrame, group_col: str, value_col: str) -> Dict[str, Any]:
        """One-way ANOVA with post-hoc Tukey HSD."""
        err = self._require_scipy()
        if err:
            return {"error": err}
        groups_data = [group[value_col].dropna() for name, group in df.groupby(group_col)]
        if len(groups_data) < 2:
            return {"error": "Need at least 2 groups for ANOVA"}
        f_stat, p_val = f_oneway(*groups_data)
        # Effect size (eta-squared)
        all_values = pd.concat(groups_data)
        grand_mean = all_values.mean()
        ss_between = sum(len(g) * (g.mean() - grand_mean)**2 for g in groups_data)
        ss_total_val = sum((v - grand_mean)**2 for v in all_values)
        eta_sq = ss_between / ss_total_val if ss_total_val != 0 else 0
        # Post-hoc Tukey
        try:
            tukey = pairwise_tukeyhsd(df[value_col], df[group_col])
            posthoc_df = pd.DataFrame({
                "Group 1": tukey.groupsunique[tukey.pairs[:, 0]],
                "Group 2": tukey.groupsunique[tukey.pairs[:, 1]],
                "Mean Diff": tukey.meandiffs,
                "p-value": tukey.pvalues,
                "Significant": tukey.reject,
            })
        except Exception:
            posthoc_df = pd.DataFrame({"Note": ["Post-hoc failed  try with more data"]})
        return {
            "test": "One-Way ANOVA",
            "num_groups": len(groups_data),
            "total_n": len(all_values),
            "f_statistic": round(float(f_stat), 4),
            "p_value": round(float(p_val), 4),
            "eta_squared": round(float(eta_sq), 4),
            "significant": p_val < 0.05,
            "post_hoc": posthoc_df,
        }

    def anova_two_way(self, df: pd.DataFrame, factor1: str, factor2: str, value_col: str) -> pd.DataFrame:
        """Two-way ANOVA using pingouin."""
        err = self._require_pingouin()
        if err:
            return pd.DataFrame({"error": [err]})
        try:
            aov = pg.anova(dv=value_col, between=[factor1, factor2], data=df, detailed=True)
            return aov
        except Exception as e:
            return pd.DataFrame({"error": [str(e)]})

    # ─── CHI-SQUARE ─────────────────────────────────────────────────
    def chi_square_test(self, df: pd.DataFrame, col1: str, col2: str) -> Dict[str, Any]:
        """Chi-square test of independence with Cramer's V."""
        err = self._require_scipy()
        if err:
            return {"error": err}
        contingency = pd.crosstab(df[col1], df[col2])
        chi2, p_val, dof, expected = chi2_contingency(contingency)
        # Cramer's V
        n = contingency.sum().sum()
        min_dim = min(contingency.shape) - 1
        cramers_v = np.sqrt(chi2 / (n * min_dim)) if n * min_dim > 0 else 0
        return {
            "test": "Chi-Square Test of Independence",
            "chi_square": round(float(chi2), 4),
            "degrees_of_freedom": int(dof),
            "p_value": round(float(p_val), 4),
            "cramers_v": round(float(cramers_v), 4),
            "sample_size": int(n),
            "significant": p_val < 0.05,
            "contingency_table": contingency,
            "expected_table": pd.DataFrame(expected, index=contingency.index, columns=contingency.columns),
        }

    # ─── CORRELATION ────────────────────────────────────────────────
    def pearson_correlation(self, df: pd.DataFrame, col1: str, col2: str) -> Dict[str, Any]:
        """Pearson correlation coefficient."""
        err = self._require_scipy()
        if err:
            return {"error": err}
        valid = df[[col1, col2]].dropna()
        if len(valid) < 3:
            return {"error": "Need at least 3 observations"}
        r, p_val = pearsonr(valid[col1], valid[col2])
        return {
            "test": "Pearson Correlation",
            "n": len(valid),
            "r": round(float(r), 4),
            "r_squared": round(float(r**2), 4),
            "p_value": round(float(p_val), 4),
            "significant": p_val < 0.05,
            "strength": "very strong" if abs(r) > 0.8 else "strong" if abs(r) > 0.6 else "moderate" if abs(r) > 0.4 else "weak",
        }

    def spearman_correlation(self, df: pd.DataFrame, col1: str, col2: str) -> Dict[str, Any]:
        """Spearman rank correlation."""
        err = self._require_scipy()
        if err:
            return {"error": err}
        valid = df[[col1, col2]].dropna()
        if len(valid) < 3:
            return {"error": "Need at least 3 observations"}
        rho, p_val = spearmanr(valid[col1], valid[col2])
        return {
            "test": "Spearman Rank Correlation",
            "n": len(valid),
            "rho": round(float(rho), 4),
            "p_value": round(float(p_val), 4),
            "significant": p_val < 0.05,
        }

    def correlation_matrix(self, df: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
        """Compute full correlation matrix for numeric columns."""
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            return pd.DataFrame()
        return numeric_df.corr(method=method)

    # ─── REGRESSION ─────────────────────────────────────────────────
    def linear_regression(self, df: pd.DataFrame, target: str, features: List[str]) -> Dict[str, Any]:
        """Simple/multiple linear regression using pingouin."""
        err = self._require_pingouin()
        if err:
            return {"error": err}
        try:
            result = pg.linear_regression(df[features], df[target])
            return {"summary": result}
        except Exception as e:
            return {"error": str(e)}

    def logistic_regression(self, df: pd.DataFrame, target: str, features: List[str]) -> Dict[str, Any]:
        """Logistic regression using pingouin."""
        err = self._require_pingouin()
        if err:
            return {"error": err}
        try:
            result = pg.logistic_regression(df[features], df[target])
            return {"summary": result}
        except Exception as e:
            return {"error": str(e)}

    # ─── NON-PARAMETRIC TESTS ───────────────────────────────────────
    def mann_whitney(self, df: pd.DataFrame, group_col: str, value_col: str) -> Dict[str, Any]:
        """Mann-Whitney U test (non-parametric alternative to independent t-test)."""
        err = self._require_scipy()
        if err:
            return {"error": err}
        groups = df[group_col].dropna().unique()
        if len(groups) != 2:
            return {"error": "Exactly 2 groups required"}
        group1 = df[df[group_col] == groups[0]][value_col].dropna()
        group2 = df[df[group_col] == groups[1]][value_col].dropna()
        if len(group1) < 2 or len(group2) < 2:
            return {"error": "Each group needs at least 2 observations"}
        u_stat, p_val = mannwhitneyu(group1, group2, alternative="two-sided")
        return {
            "test": "Mann-Whitney U Test",
            "u_statistic": round(float(u_stat), 4),
            "p_value": round(float(p_val), 4),
            "median_1": round(float(group1.median()), 4),
            "median_2": round(float(group2.median()), 4),
            "significant": p_val < 0.05,
        }

    def kruskal_wallis(self, df: pd.DataFrame, group_col: str, value_col: str) -> Dict[str, Any]:
        """Kruskal-Wallis H test (non-parametric alternative to one-way ANOVA)."""
        err = self._require_scipy()
        if err:
            return {"error": err}
        groups_data = [group[value_col].dropna() for name, group in df.groupby(group_col)]
        if len(groups_data) < 2:
            return {"error": "Need at least 2 groups"}
        h_stat, p_val = kruskal(*groups_data)
        return {
            "test": "Kruskal-Wallis H Test",
            "h_statistic": round(float(h_stat), 4),
            "p_value": round(float(p_val), 4),
            "degrees_of_freedom": len(groups_data) - 1,
            "significant": p_val < 0.05,
        }

    def wilcoxon_signed_rank(self, df: pd.DataFrame, before_col: str, after_col: str) -> Dict[str, Any]:
        """Wilcoxon signed-rank test (non-parametric paired t-test)."""
        err = self._require_scipy()
        if err:
            return {"error": err}
        valid = df[[before_col, after_col]].dropna()
        if len(valid) < 3:
            return {"error": "Need at least 3 paired observations"}
        w_stat, p_val = wilcoxon(valid[before_col], valid[after_col])
        return {
            "test": "Wilcoxon Signed-Rank Test",
            "w_statistic": round(float(w_stat), 4),
            "p_value": round(float(p_val), 4),
            "n_pairs": len(valid),
            "significant": p_val < 0.05,
        }

    # ─── NORMALITY TESTS ────────────────────────────────────────────
    def test_normality(self, df: pd.DataFrame, col: str) -> Dict[str, Any]:
        """Shapiro-Wilk test for normality."""
        err = self._require_scipy()
        if err:
            return {"error": err}
        series = df[col].dropna()
        if len(series) < 3:
            return {"error": "Need at least 3 observations"}
        if len(series) > 5000:
            # Use Kolmogorov-Smirnov for large samples
            stat, p_val = kstest(series, "norm", args=(series.mean(), series.std()))
            test_name = "Kolmogorov-Smirnov Test"
        else:
            stat, p_val = shapiro(series)
            test_name = "Shapiro-Wilk Test"
        return {
            "test": test_name,
            "statistic": round(float(stat), 4),
            "p_value": round(float(p_val), 4),
            "is_normal": p_val > 0.05,
            "n": len(series),
        }

    # ─── POWER ANALYSIS ─────────────────────────────────────────────
    def power_ttest(self, effect_size: float = 0.5, alpha: float = 0.05, power: float = 0.8, ratio: float = 1.0) -> Dict[str, Any]:
        """Power analysis for t-test  estimate required sample size."""
        err = self._require_statsmodels()
        if err:
            return {"error": err}
        analysis = TTestIndPower()
        n = analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power, ratio=ratio)
        return {
            "test": "Power Analysis (Independent T-Test)",
            "effect_size": effect_size,
            "alpha": alpha,
            "desired_power": power,
            "required_n_per_group": int(np.ceil(n)),
            "total_n": int(np.ceil(n * (1 + ratio))),
        }

    # ─── RELIABILITY ANALYSIS ───────────────────────────────────────
    def cronbach_alpha(self, df: pd.DataFrame, items: List[str]) -> Dict[str, Any]:
        """Cronbach's alpha for scale reliability."""
        err = self._require_pingouin()
        if err:
            return {"error": err}
        try:
            alpha = pg.cronbach_alpha(df[items])
            return {
                "test": "Cronbach's Alpha",
                "alpha": round(float(alpha[0]), 4),
                "items": len(items),
                "n": len(df),
                "interpretation": "Excellent" if alpha[0] >= 0.9 else "Good" if alpha[0] >= 0.8 else "Acceptable" if alpha[0] >= 0.7 else "Questionable" if alpha[0] >= 0.6 else "Poor",
            }
        except Exception as e:
            return {"error": str(e)}

    # ─── FACTOR ANALYSIS ────────────────────────────────────────────
    def kmo_test(self, df: pd.DataFrame, variables: List[str]) -> Dict[str, Any]:
        """Kaiser-Meyer-Olkin measure of sampling adequacy."""
        try:
            from factor_analyzer.factor_analyzer import calculate_kmo
            kmo_all, kmo_per_var = calculate_kmo(df[variables])
            return {
                "test": "KMO Test",
                "kmo_overall": round(float(kmo_all), 4),
                "kmo_per_variable": dict(zip(variables, [round(v, 4) for v in kmo_per_var])),
                "interpretation": "Meritorious" if kmo_all >= 0.8 else "Middling" if kmo_all >= 0.7 else "Mediocre" if kmo_all >= 0.6 else "Unacceptable",
            }
        except ImportError:
            return {"error": "factor_analyzer not installed. Install with: pip install factor-analyzer"}
        except Exception as e:
            return {"error": str(e)}

    def bartlett_test(self, df: pd.DataFrame, variables: List[str]) -> Dict[str, Any]:
        """Bartlett's test of sphericity."""
        try:
            from factor_analyzer.factor_analyzer import calculate_bartlett_sphericity
            chi_square, p_val = calculate_bartlett_sphericity(df[variables])
            return {
                "test": "Bartlett's Test of Sphericity",
                "chi_square": round(float(chi_square), 4),
                "p_value": round(float(p_val), 4),
                "significant": p_val < 0.05,
            }
        except ImportError:
            return {"error": "factor_analyzer not installed"}
        except Exception as e:
            return {"error": str(e)}

    # ─── DESCRIPTIVE BY GROUP ───────────────────────────────────────
    def descriptive_by_group(self, df: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
        """Descriptive statistics grouped by a categorical variable."""
        return df.groupby(group_col)[value_col].describe().round(4)

