import security_guard

"""
Executive Auto-Insight Storyteller  automatically runs statistical test batteries
on data load and generates a beautifully formatted executive summary,
risk assessment, and core takeaways.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st

from modules.data_processor import infer_column_types, profile_dataset
from modules.statistical_engine import StatisticalEngine
from modules.ai_analyzer import CHRISHEMAnalyzer
from modules.logging_utils import get_logger

logger = get_logger(__name__)


class ExecutiveStoryteller:
    """
    Triggers on data load. Runs automated statistical tests, anomaly detection,
    correlation analysis, and uses templated LLM-style narrative generation
    to produce an executive-grade report.
    """

    def __init__(self):
        self.stats = StatisticalEngine()
        self.analyzer = CHRISHEMAnalyzer()
        self.report_generated = False

    def generate_executive_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run the full automated executive analysis pipeline."""
        if df is None or df.empty:
            return {"error": "No data available", "executive_summary": "", "risk_assessment": "", "takeaways": []}

        profile = profile_dataset(df)
        col_types = infer_column_types(df)
        numeric_cols = [c for c, t in col_types.items() if t in ("numeric", "integer")]
        cat_cols = [c for c, t in col_types.items() if t in ("categorical", "string")]
        temporal_cols = [c for c, t in col_types.items() if t == "temporal"]

        # â”€â”€â”€ 1. Automated Statistical Test Battery â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        test_battery = self._run_test_battery(df, numeric_cols, cat_cols, temporal_cols)

        # â”€â”€â”€ 2. Anomaly Detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        anomalies = self._detect_anomalies(df, numeric_cols)

        # â”€â”€â”€ 3. Correlation Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        correlations = self._analyze_correlations(df, numeric_cols)

        # â”€â”€â”€ 4. Data Quality Assessment â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        quality = self._assess_quality(df, profile)

        # â”€â”€â”€ 5. Generate Narrative â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        executive_summary = self._generate_executive_summary(df, profile, test_battery, correlations)
        risk_assessment = self._generate_risk_assessment(quality, anomalies, test_battery)
        takeaways = self._generate_takeaways(df, test_battery, correlations, anomalies, quality)

        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dataset": {
                "name": st.session_state.get("data_source", "Unknown"),
                "rows": profile["rows"],
                "columns": profile["columns"],
                "numeric_vars": len(numeric_cols),
                "categorical_vars": len(cat_cols),
                "temporal_vars": len(temporal_cols),
            },
            "test_battery": test_battery,
            "anomalies": anomalies,
            "correlations": correlations,
            "quality": quality,
            "executive_summary": executive_summary,
            "risk_assessment": risk_assessment,
            "takeaways": takeaways,
            "severity": self._compute_overall_severity(quality, anomalies, test_battery),
        }

        self.report_generated = True
        st.session_state["executive_report"] = report
        st.session_state["executive_report_generated"] = True
        return report

    def _run_test_battery(self, df: pd.DataFrame, numeric_cols: List[str],
                          cat_cols: List[str], temporal_cols: List[str]) -> Dict[str, Any]:
        """Run a comprehensive battery of automated statistical tests."""
        battery = {
            "tests_run": 0,
            "significant_findings": 0,
            "tests": [],
        }

        # One-sample t-tests on numeric columns
        for col in numeric_cols[:5]:
            try:
                result = self.stats.one_sample_ttest(df, col, 0)
                if "error" not in result:
                    battery["tests_run"] = 1
                    if result.get("significant"):
                        battery["significant_findings"] = 1
                        battery["tests"].append({
                            "type": "one_sample_ttest",
                            "variable": col,
                            "result": result,
                            "narrative": f"**{col}** mean ({result.get('mean', 0):.2f}) is significantly different from 0 "
                                        f"(t({result.get('n', 0)-1}) = {result.get('t_statistic', 0):.2f}, p = {result.get('p_value', 1):.3f}, d = {result.get('cohens_d', 0):.2f})",
                        })
            except Exception:
                logger.warning("One-sample t-test failed for column %r", col, exc_info=True)

        # Group comparisons
        for cat in cat_cols[:3]:
            for num in numeric_cols[:3]:
                try:
                    n_groups = df[cat].nunique()
                    if n_groups == 2:
                        result = self.stats.independent_ttest(df, cat, num)
                        if "error" not in result and result.get("significant"):
                            battery["tests_run"] = 1
                            battery["significant_findings"] = 1
                            battery["tests"].append({
                                "type": "independent_ttest",
                                "group_var": cat,
                                "value_var": num,
                                "result": result,
                                "narrative": f"**{num}** differs significantly between groups of **{cat}** "
                                            f"(t = {result.get('t_statistic', 0):.2f}, p = {result.get('p_value', 1):.3f}, d = {result.get('cohens_d', 0):.2f})",
                            })
                    elif n_groups >= 3:
                        result = self.stats.anova_one_way(df, cat, num)
                        if "error" not in result and result.get("significant"):
                            battery["tests_run"] = 1
                            battery["significant_findings"] = 1
                            battery["tests"].append({
                                "type": "anova",
                                "group_var": cat,
                                "value_var": num,
                                "result": result,
                                "narrative": f"**{num}** varies significantly across {n_groups} groups of **{cat}** "
                                            f"(F = {result.get('f_statistic', 0):.2f}, p = {result.get('p_value', 1):.3f}, Î·Â² = {result.get('eta_squared', 0):.2f})",
                            })
                except Exception:
                    logger.warning("Group comparison failed for %r by %r", num, cat, exc_info=True)

        # Chi-square tests
        for i, cat1 in enumerate(cat_cols[:4]):
            for cat2 in cat_cols[i1:4]:
                try:
                    result = self.stats.chi_square_test(df, cat1, cat2)
                    if "error" not in result and result.get("significant"):
                        battery["tests_run"] = 1
                        battery["significant_findings"] = 1
                        battery["tests"].append({
                            "type": "chi_square",
                            "var1": cat1,
                            "var2": cat2,
                            "result": result,
                            "narrative": f"**{cat1}** and **{cat2}** are significantly associated "
                                        f"(Ï‡Â² = {result.get('chi_square', 0):.2f}, p = {result.get('p_value', 1):.3f}, V = {result.get('cramers_v', 0):.2f})",
                        })
                except Exception:
                    logger.warning("Chi-square test failed for %r vs %r", cat1, cat2, exc_info=True)

        # Correlation tests
        if len(numeric_cols) >= 2:
            strong_corrs = []
            for i, col1 in enumerate(numeric_cols[:6]):
                for col2 in numeric_cols[i1:6]:
                    try:
                        result = self.stats.pearson_correlation(df, col1, col2)
                        if "error" not in result and result.get("significant") and abs(result.get("r", 0)) > 0.3:
                            battery["tests_run"] = 1
                            if abs(result.get("r", 0)) > 0.5:
                                battery["significant_findings"] = 1
                                strong_corrs.append({
                                    "var1": col1, "var2": col2,
                                    "r": result.get("r", 0),
                                    "narrative": f"Strong correlation: **{col1}** â†” **{col2}** "
                                                f"(r = {result.get('r', 0):.2f}, p = {result.get('p_value', 1):.3f})",
                                })
                    except Exception:
                        logger.warning("Correlation test failed for %r vs %r", col1, col2, exc_info=True)
            battery["strong_correlations"] = strong_corrs

        # Temporal trends
        if temporal_cols and numeric_cols:
            for temp in temporal_cols[:1]:
                for num in numeric_cols[:2]:
                    try:
                        temp_ord = pd.to_datetime(df[temp]).astype('int64') // 10**9
                        from scipy import stats as scipy_stats
                        r, p = scipy_stats.spearmanr(temp_ord.dropna(), df[num].dropna())
                        if not np.isnan(r) and p < 0.05 and abs(r) > 0.3:
                            battery["tests_run"] = 1
                            battery["significant_findings"] = 1
                            direction = "increasing" if r > 0 else "decreasing"
                            battery["tests"].append({
                                "type": "temporal_trend",
                                "temporal_var": temp,
                                "value_var": num,
                                "rho": round(float(r), 4),
                                "p_value": round(float(p), 4),
                                "narrative": f"**{num}** shows a significant {direction} trend over time "
                                            f"(Ï = {r:.2f}, p = {p:.3f})",
                            })
                    except Exception:
                        logger.warning("Temporal trend test failed for %r over %r", num, temp, exc_info=True)

        return battery

    def _detect_anomalies(self, df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Any]:
        """Detect anomalies/outliers across the dataset."""
        anomalies = {"columns_with_outliers": 0, "total_outliers": 0, "details": []}

        for col in numeric_cols:
            try:
                series = df[col].dropna()
                if len(series) < 10:
                    continue
                q1 = series.quantile(0.25)
                q3 = series.quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3  1.5 * iqr
                outliers = series[(series < lower) | (series > upper)]
                if len(outliers) > 0:
                    anomalies["columns_with_outliers"] = 1
                    anomalies["total_outliers"] = len(outliers)
                    anomalies["details"].append({
                        "column": col,
                        "outlier_count": int(len(outliers)),
                        "outlier_pct": round(float(len(outliers) / len(series) * 100), 1),
                        "lower_bound": round(float(lower), 2),
                        "upper_bound": round(float(upper), 2),
                    })
            except Exception:
                logger.warning("Outlier detection failed for column %r", col, exc_info=True)

        anomalies["severity"] = (
            "low" if anomalies["total_outliers"] < 10
            else "medium" if anomalies["total_outliers"] < 50
            else "high"
        )
        return anomalies

    def _analyze_correlations(self, df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Any]:
        """Analyze correlation structure."""
        if len(numeric_cols) < 2:
            return {"message": "Need at least 2 numeric columns", "strong_pairs": []}

        corr_matrix = df[numeric_cols].corr()
        strong_pairs = []
        for i in range(len(numeric_cols)):
            for j in range(i  1, len(numeric_cols)):
                r = corr_matrix.iloc[i, j]
                if abs(r) >= 0.5:
                    strong_pairs.append({
                        "var1": numeric_cols[i],
                        "var2": numeric_cols[j],
                        "r": round(float(r), 4),
                        "strength": "very strong" if abs(r) >= 0.8 else "strong",
                    })

        return {
            "strong_pairs": strong_pairs,
            "total_pairs_above_0.5": len(strong_pairs),
            "correlation_matrix": corr_matrix,
        }

    def _assess_quality(self, df: pd.DataFrame, profile: Dict) -> Dict[str, Any]:
        """Assess data quality."""
        quality = {"score": 100, "issues": [], "warnings": []}

        missing_pct = profile.get("missing_pct", 0)
        if missing_pct > 20:
            quality["score"] -= 25
            quality["issues"].append(f"âš ï¸ High missing data rate ({missing_pct}%)")
        elif missing_pct > 10:
            quality["score"] -= 15
            quality["issues"].append(f"âš ï¸ Moderate missing data rate ({missing_pct}%)")
        elif missing_pct > 0:
            quality["warnings"].append(f"ðŸ“‹ Minimal missing data ({missing_pct}%)")

        duplicates = profile.get("duplicate_rows", 0)
        if duplicates > 0:
            quality["score"] -= 10
            quality["issues"].append(f"âš ï¸ {duplicates} duplicate rows detected")

        n_rows = profile.get("rows", 0)
        if n_rows < 30:
            quality["score"] -= 15
            quality["issues"].append(f"âš ï¸ Small sample size (N={n_rows})  results may be unstable")
        elif n_rows < 100:
            quality["warnings"].append(f"ðŸ“‹ Moderate sample size (N={n_rows})")

        numeric_cols = profile.get("numeric_columns", [])
        if len(numeric_cols) < 2:
            quality["warnings"].append("ðŸ“‹ Few numeric variables  limited statistical analysis available")

        quality["score"] = max(0, quality["score"])
        quality["grade"] = "A" if quality["score"] >= 90 else "B" if quality["score"] >= 75 else "C" if quality["score"] >= 60 else "D"
        return quality

    def _generate_executive_summary(self, df: pd.DataFrame, profile: Dict,
                                     test_battery: Dict, correlations: Dict) -> str:
        """Generate a formatted executive summary."""
        lines = []
        lines.append(f"##  Executive Data Summary")
        lines.append(f"")
        lines.append(f"**Dataset**: {profile['rows']:,} observations Ã— {profile['columns']} variables")
        lines.append(f"**Analysis Time**: {datetime.now():%Y-%m-%d %H:%M}")
        lines.append(f"")

        # Key metrics
        sig_count = test_battery.get("significant_findings", 0)
        total_tests = test_battery.get("tests_run", 0)
        strong_corrs = len(correlations.get("strong_pairs", []))

        lines.append(f"### ðŸ“ˆ Key Metrics")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Statistical Tests Run | {total_tests} |")
        lines.append(f"| Significant Findings | {sig_count} |")
        lines.append(f"| Strong Correlations (|r| â‰¥ 0.5) | {strong_corrs} |")
        lines.append(f"| Data Quality Score | {profile.get('missing_pct', 0):.1f}% missing |")
        lines.append(f"")

        # Top findings
        if test_battery.get("tests"):
            lines.append(f"### ðŸ† Top Statistical Findings")
            for i, test in enumerate(test_battery["tests"][:5]):
                lines.append(f"{i1}. {test.get('narrative', '')}")
            lines.append(f"")

        if strong_corrs > 0:
            lines.append(f"### ðŸ”— Key Relationships")
            for pair in correlations["strong_pairs"][:3]:
                lines.append(f"- **{pair['var1']}** â†” **{pair['var2']}**: r = {pair['r']:.2f} ({pair['strength']})")
            lines.append(f"")

        return "\n".join(lines)

    def _generate_risk_assessment(self, quality: Dict, anomalies: Dict, test_battery: Dict) -> str:
        """Generate risk assessment narrative."""
        lines = []
        lines.append(f"## âš ï¸ Risk Assessment")
        lines.append(f"")

        quality_grade = quality.get("grade", "N/A")
        quality_score = quality.get("score", 0)
        lines.append(f"**Data Quality Grade**: {quality_grade} (Score: {quality_score}/100)")
        lines.append(f"")

        if quality.get("issues"):
            lines.append(f"### Data Quality Risks")
            for issue in quality["issues"]:
                lines.append(f"- {issue}")
            lines.append(f"")

        if quality.get("warnings"):
            lines.append(f"### Cautions")
            for warning in quality["warnings"]:
                lines.append(f"- {warning}")
            lines.append(f"")

        if anomalies.get("total_outliers", 0) > 0:
            severity = anomalies.get("severity", "low")
            sev_icon = "ðŸ”´" if severity == "high" else "ðŸŸ¡" if severity == "medium" else "ðŸŸ¢"
            lines.append(f"### Outlier Risk {sev_icon}")
            lines.append(f"- {anomalies['total_outliers']} outliers detected across {anomalies['columns_with_outliers']} columns ({severity} severity)")
            lines.append(f"")

        # Statistical risks
        if test_battery.get("tests_run") == 0:
            lines.append(f"### ðŸ”¬ Statistical Limitations")
            lines.append(f"- No significant statistical findings  data may lack power or structure")
            lines.append(f"")

        lines.append(f"### ðŸ’¡ Recommendations")
        if quality_score < 70:
            lines.append(f"- **Clean your data**: Address missing values and outliers before drawing conclusions")
        if anomalies.get("total_outliers", 0) > 0:
            lines.append(f"- **Review outliers**: Consider winsorization or robust statistical methods")
        lines.append(f"- **Validate findings**: Cross-validate key results with holdout samples")
        lines.append(f"- **Document assumptions**: Clearly state all analytical decisions for reproducibility")

        return "\n".join(lines)

    def _generate_takeaways(self, df: pd.DataFrame, test_battery: Dict,
                             correlations: Dict, anomalies: Dict, quality: Dict) -> List[Dict]:
        """Generate actionable core takeaways."""
        takeaways = []

        # Finding-based takeaways
        for test in test_battery.get("tests", [])[:3]:
            takeaways.append({
                "type": "finding",
                "severity": "high" if test.get("result", {}).get("p_value", 1) < 0.01 else "medium",
                "icon": "ðŸ”¬",
                "text": test.get("narrative", "").replace("**", ""),
            })

        # Correlation takeaways
        for pair in correlations.get("strong_pairs", [])[:2]:
            takeaways.append({
                "type": "relationship",
                "severity": "medium",
                "icon": "ðŸ”—",
                "text": f"Strong {'positive' if pair['r'] > 0 else 'negative'} relationship between {pair['var1']} and {pair['var2']} (r = {pair['r']:.2f})",
            })

        # Quality takeaways
        if quality.get("issues"):
            for issue in quality["issues"][:2]:
                takeaways.append({
                    "type": "quality",
                    "severity": "high" if "High" in issue else "medium",
                    "icon": "âš ï¸",
                    "text": issue.replace("âš ï¸ ", ""),
                })

        # Anomaly takeaways
        if anomalies.get("total_outliers", 0) > 0:
            takeaways.append({
                "type": "anomaly",
                "severity": anomalies.get("severity", "low"),
                "icon": "",
                "text": f"{anomalies['total_outliers']} anomalous data points detected  review before modeling",
            })

        # Data size takeaways
        n = len(df)
        if n > 10000:
            takeaways.append({
                "type": "scale",
                "severity": "low",
                "icon": "ðŸ“",
                "text": f"Large dataset ({n:,} rows)  consider sampling for faster iterative analysis",
            })
        elif n < 50:
            takeaways.append({
                "type": "scale",
                "severity": "high",
                "icon": "ðŸ“",
                "text": f"Small dataset ({n} rows)  interpret results with caution, consider Bayesian methods",
            })

        # Sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        takeaways.sort(key=lambda t: severity_order.get(t["severity"], 3))

        return takeaways

    def _compute_overall_severity(self, quality: Dict, anomalies: Dict, test_battery: Dict) -> str:
        """Compute overall severity level."""
        risks = 0
        if quality.get("score", 100) < 70:
            risks = 2
        if anomalies.get("severity") == "high":
            risks = 2
        elif anomalies.get("severity") == "medium":
            risks = 1
        if test_battery.get("significant_findings", 0) == 0 and test_battery.get("tests_run", 0) > 3:
            risks = 1

        if risks >= 3:
            return "high"
        elif risks >= 1:
            return "medium"
        return "low"


# â”€â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def render_executive_storyteller_ui():
    """Render the executive storyteller report in a beautifully formatted UI."""
    report = st.session_state.get("executive_report")
    if not report:
        st.info("ðŸ‘† The executive report will auto-generate when data is loaded.")
        return

    severity = report.get("severity", "medium")
    severity_colors = {"low": "#2ecc71", "medium": "#e67e22", "high": "#e74c3c"}
    severity_color = severity_colors.get(severity, "#64748b")

    # â”€â”€â”€ Severity Banner â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.markdown(f"""
    <div style="text-align:center;padding:0.8rem;border-radius:14px;
                border:2px solid {severity_color};background:{severity_color}10;margin-bottom:1rem;">
        <span style="font-size:1.1rem;font-weight:700;color:{severity_color};">
            {'ðŸŸ¢ LOW RISK' if severity == 'low' else 'ðŸŸ¡ MODERATE RISK' if severity == 'medium' else 'ðŸ”´ HIGH RISK'}
        </span>
        <span style="color:#64748b;margin-left:1rem;">
            Overall Assessment  Generated {report.get('generated_at', '')}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # â”€â”€â”€ Dataset Overview â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ds = report.get("dataset", {})
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(" Rows", f"{ds.get('rows', 0):,}")
    with col2:
        st.metric("ðŸ“‹ Columns", ds.get("columns", 0))
    with col3:
        st.metric("ðŸ”¬ Tests Run", report.get("test_battery", {}).get("tests_run", 0))
    with col4:
        st.metric("ðŸ’¡ Significant", report.get("test_battery", {}).get("significant_findings", 0))

    # â”€â”€â”€ Executive Summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.markdown("---")
    st.markdown(report.get("executive_summary", ""), unsafe_allow_html=True)

    # â”€â”€â”€ Detailed Tests â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    tests = report.get("test_battery", {}).get("tests", [])
    if tests:
        with st.expander("ðŸ” View All Statistical Test Results", expanded=False):
            for test in tests:
                p = test.get("result", {}).get("p_value", 1)
                sig_badge = "âœ… Significant" if p < 0.05 else "âŒ Not significant"
                p_str = f"p = {p:.4f}" if p >= 0.0001 else "p < .0001"
                st.markdown(f"""
                <div style="padding:0.6rem;margin:0.3rem 0;border-radius:8px;
                            border-left:4px solid {'#2ecc71' if p < 0.05 else '#e74c3c'};
                            background:rgba(0,0,0,0.02);">
                    <span style="font-weight:600;">{test.get('narrative', '')}</span>
                    <span style="margin-left:0.5rem;font-size:0.85rem;color:#64748b;">| {sig_badge} ({p_str})</span>
                </div>
                """, unsafe_allow_html=True)

    # â”€â”€â”€ Strong Correlations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    strong_pairs = report.get("correlations", {}).get("strong_pairs", [])
    if strong_pairs:
        with st.expander("ðŸ”— View Strong Correlations", expanded=False):
            for pair in strong_pairs:
                st.markdown(f"- **{pair['var1']}** â†” **{pair['var2']}**: r = {pair['r']:.2f} ({pair['strength']})")

    # â”€â”€â”€ Risk Assessment â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.markdown("---")
    st.markdown(report.get("risk_assessment", ""), unsafe_allow_html=True)

    # â”€â”€â”€ Core Takeaways â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.markdown("---")
    st.markdown("## ðŸŽ¯ Core Takeaways")
    takeaways = report.get("takeaways", [])
    if takeaways:
        for t in takeaways:
            sev = t.get("severity", "low")
            colors = {"high": "#e74c3c", "medium": "#e67e22", "low": "#2ecc71"}
            color = colors.get(sev, "#64748b")
            st.markdown(f"""
            <div style="padding:0.7rem 1rem;margin:0.4rem 0;border-radius:10px;
                        border-left:4px solid {color};background:{color}08;">
                <span style="font-size:1.1rem;">{t.get('icon', '')}</span>
                <span style="font-weight:500;">{t.get('text', '')}</span>
            </div>
            """, unsafe_allow_html=True)

    # â”€â”€â”€ Export â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        report_text = f"""# Executive Analysis Report
{report.get('executive_summary', '')}

## Risk Assessment
{report.get('risk_assessment', '')}

## Core Takeaways
{chr(10).join([f"- [{t.get('severity','').upper()}] {t.get('text','')}" for t in takeaways])}

---
Generated by CHRISHEM Executive Storyteller
"""
        if st.button("ðŸ“‹ Copy Report to Clipboard"):
            st.code(report_text, language="markdown")
    with col2:
        import base64
        b64 = base64.b64encode(report_text.encode()).decode()
        st.markdown(
            f'<a href="data:text/markdown;base64,{b64}" download="executive_report_{datetime.now():%Y%m%d}.md">'
            f'ðŸ“¥ Download Report (Markdown)</a>',
            unsafe_allow_html=True,
        )

