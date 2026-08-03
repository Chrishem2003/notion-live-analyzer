import security_guard
import security_guard

"""
CHRISHEM Analyzer  automated data analysis, profiling, and insight generation.
Provides smart test recommendations and natural language insights.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

# Local imports
from modules.data_processor import (
    infer_column_types, profile_dataset, get_column_summary,
    detect_outliers_iqr, detect_outliers_zscore,
)
from modules.statistical_engine import StatisticalEngine
from modules.logging_utils import get_logger

logger = get_logger(__name__)


class CHRISHEMAnalyzer:
    """Automated CHRISHEM-powered data analysis engine."""

    def __init__(self):
        self.stats = StatisticalEngine()

    # â”€â”€â”€ Full Automated Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def auto_analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run a complete automated analysis pipeline on the dataset."""
        if df is None or df.empty:
            return {"error": "No data to analyze"}

        results = {
            "profile": self.profile_dataset(df),
            "missing": self.analyze_missing(df),
            "outliers": self.find_outliers(df),
            "normality": self.test_normality_all(df),
            "correlations": self.find_correlations(df),
            "recommendations": self.recommend_tests(df),
            "insights": self.generate_insights(df),
            "visualizations": self.recommend_visualizations(df),
        }
        return results

    # â”€â”€â”€ Dataset Profiling â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def profile_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate a human-readable data profile."""
        profile = profile_dataset(df)
        col_types = profile["column_types"]

        type_summary = {}
        for col, ctype in col_types.items():
            if ctype not in type_summary:
                type_summary[ctype] = []
            type_summary[ctype].append(col)

        summary_lines = [
            f" **Dataset Overview**: {profile['rows']:,} rows Ã— {profile['columns']} columns",
            f"ðŸ“¦ **Memory Usage**: {profile['memory_usage'] / 1024:.1f} KB",
            f"â¬œ **Missing Values**: {profile['missing_cells']:,} ({profile['missing_pct']}%)",
            f"ðŸ” **Duplicate Rows**: {profile['duplicate_rows']:,}",
        ]

        for dtype, cols in type_summary.items():
            summary_lines.append(f"  â€¢ **{dtype}**: {len(cols)} columns  {', '.join(cols[:5])}{'...' if len(cols) > 5 else ''}")

        return {
            "raw": profile,
            "summary": "\n".join(summary_lines),
            "type_summary": type_summary,
        }

    # â”€â”€â”€ Missing Value Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def analyze_missing(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze missing values across the dataset."""
        missing_df = pd.DataFrame({
            "Column": df.columns,
            "Missing": df.isna().sum().values,
            "Percentage": (df.isna().mean() * 100).round(2).values,
        })
        missing_df = missing_df[missing_df["Missing"] > 0].sort_values("Percentage", ascending=False)

        if missing_df.empty:
            return {
                "has_missing": False,
                "message": "âœ… No missing values found in the dataset.",
                "data": missing_df,
            }

        total_missing = missing_df["Missing"].sum()
        total_cells = df.shape[0] * df.shape[1]
        severity = "low" if total_missing / total_cells < 0.05 else "medium" if total_missing / total_cells < 0.2 else "high"

        suggestions = []
        if severity == "high":
            suggestions.append("âš ï¸ High missing rate  consider removing or imputing affected columns")
        for _, row in missing_df.iterrows():
            if row["Percentage"] > 50:
                suggestions.append(f"  â€¢ `{row['Column']}` is {row['Percentage']}% missing  consider dropping")

        return {
            "has_missing": True,
            "severity": severity,
            "total_missing": int(total_missing),
            "message": f"âš ï¸ Found **{int(total_missing):,}** missing values ({severity} severity)",
            "suggestions": suggestions,
            "data": missing_df,
        }

    # â”€â”€â”€ Outlier Detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def find_outliers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect outliers in numeric columns."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        outlier_results = {}

        for col in numeric_cols:
            if df[col].nunique() < 5:
                continue
            iqr_outliers = detect_outliers_iqr(df, col)
            zscore_outliers = detect_outliers_zscore(df, col)

            n_iqr = iqr_outliers.sum()
            n_zscore = zscore_outliers.sum()

            if n_iqr > 0 or n_zscore > 0:
                outlier_results[col] = {
                    "iqr_count": int(n_iqr),
                    "iqr_pct": round(float(n_iqr / len(df) * 100), 2),
                    "zscore_count": int(n_zscore),
                    "zscore_pct": round(float(n_zscore / len(df) * 100), 2),
                    "top_outliers": df.loc[iqr_outliers, col].head(5).tolist() if n_iqr > 0 else [],
                }

        n_cols_with_outliers = len(outlier_results)
        total_columns = len(numeric_cols)

        return {
            "columns_with_outliers": n_cols_with_outliers,
            "total_numeric_columns": total_columns,
            "details": outlier_results,
            "summary": f"ðŸ” Found potential outliers in **{n_cols_with_outliers}** of **{total_columns}** numeric columns" if n_cols_with_outliers > 0 else "âœ… No significant outliers detected",
        }

    # â”€â”€â”€ Normality Tests â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def test_normality_all(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Test normality for all numeric columns."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        results = {}

        for col in numeric_cols:
            if df[col].nunique() < 5:
                continue
            try:
                result = self.stats.test_normality(df, col)
                if "error" not in result:
                    results[col] = result
                else:
                    logger.warning("Normality test for %r failed: %s", col, result["error"])
            except Exception:
                logger.warning("Normality test raised for column %r", col, exc_info=True)
                continue

        normal_cols = [c for c, r in results.items() if r.get("is_normal")]
        non_normal_cols = [c for c, r in results.items() if not r.get("is_normal")]

        return {
            "columns_tested": len(results),
            "normal": normal_cols,
            "non_normal": non_normal_cols,
            "details": results,
            "summary": (
                f"ðŸ“ˆ **Normality**: {len(normal_cols)}/{len(results)} columns appear normally distributed"
                if results else "â„¹ï¸ Insufficient data for normality testing"
            ),
        }

    # â”€â”€â”€ Correlation Discovery â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def find_correlations(self, df: pd.DataFrame, threshold: float = 0.5) -> Dict[str, Any]:
        """Find strong correlations between numeric variables."""
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.shape[1] < 2:
            return {"message": "Need at least 2 numeric columns for correlation analysis"}

        corr_matrix = numeric_df.corr().abs()
        strong_pairs = []

        for i in range(len(corr_matrix.columns)):
            for j in range(i  1, len(corr_matrix.columns)):
                val = corr_matrix.iloc[i, j]
                if val >= threshold:
                    strong_pairs.append({
                        "var1": corr_matrix.columns[i],
                        "var2": corr_matrix.columns[j],
                        "correlation": round(float(val), 4),
                        "strength": "very strong" if val >= 0.8 else "strong" if val >= 0.6 else "moderate",
                    })

        strong_pairs.sort(key=lambda x: x["correlation"], reverse=True)

        if len(strong_pairs) == 0:
            weakest = []
            for i in range(min(5, len(corr_matrix.columns))):
                for j in range(i  1, min(5, len(corr_matrix.columns))):
                    val = abs(corr_matrix.iloc[i, j])
                    weakest.append({
                        "var1": corr_matrix.columns[i],
                        "var2": corr_matrix.columns[j],
                        "correlation": round(float(val), 4),
                    })
            weakest.sort(key=lambda x: x["correlation"], reverse=True)

        return {
            "strong_correlations": strong_pairs[:20],
            "top_positive": [p for p in strong_pairs if p["correlation"] >= 0][:5],
            "top_negative": [p for p in strong_pairs if p["correlation"] < 0][:5],
            "summary": (
                f"ðŸ”— Found **{len(strong_pairs)}** strong correlations (|r| â‰¥ {threshold})"
                if strong_pairs
                else "ðŸ”— No strong correlations found above threshold"
            ),
        }

    # â”€â”€â”€ Smart Test Recommendation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def recommend_tests(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Recommend appropriate statistical tests based on data structure."""
        col_types = infer_column_types(df)
        recommendations = []

        numeric_cols = [c for c, t in col_types.items() if t in ("numeric", "integer")]
        cat_cols = [c for c, t in col_types.items() if t in ("categorical", "string")]
        bool_cols = [c for c, t in col_types.items() if t == "boolean"]

        # One-sample t-test
        if numeric_cols:
            recommendations.append({
                "test": "One-Sample T-Test",
                "variables": [numeric_cols[0]],
                "description": f"Compare the mean of **{numeric_cols[0]}** against a hypothesized value (e.g., population mean)",
                "when_to_use": "When you have a single numeric variable and want to compare its mean to a known value",
                "prerequisites": "Normally distributed data",
            })

        # Independent t-test
        if len(cat_cols) >= 1 and numeric_cols:
            for cat in cat_cols:
                n_groups = df[cat].nunique()
                if n_groups == 2:
                    recommendations.append({
                        "test": "Independent Samples T-Test",
                        "variables": [cat, numeric_cols[0]],
                        "description": f"Compare **{numeric_cols[0]}** between 2 groups of **{cat}**",
                        "when_to_use": f"Compare {numeric_cols[0]} across 2 categories of {cat}",
                        "prerequisites": "Normality within groups, homogeneity of variance",
                    })
                elif n_groups >= 3:
                    recommendations.append({
                        "test": "One-Way ANOVA",
                        "variables": [cat, numeric_cols[0]],
                        "description": f"Compare **{numeric_cols[0]}** across {n_groups} groups of **{cat}**",
                        "when_to_use": f"Compare {numeric_cols[0]} across 3 groups",
                        "prerequisites": "Normality within groups, equal variances",
                    })

        # Chi-square
        if len(cat_cols) >= 2:
            recommendations.append({
                "test": "Chi-Square Test of Independence",
                "variables": [cat_cols[0], cat_cols[1]],
                "description": f"Test association between **{cat_cols[0]}** and **{cat_cols[1]}**",
                "when_to_use": "Check if two categorical variables are related",
                "prerequisites": "Expected frequency â‰¥ 5 per cell",
            })

        # Correlation
        if len(numeric_cols) >= 2:
            recommendations.extend([
                {
                    "test": "Pearson Correlation",
                    "variables": [numeric_cols[0], numeric_cols[1]],
                    "description": f"Linear relationship between **{numeric_cols[0]}** and **{numeric_cols[1]}**",
                    "when_to_use": "Measure strength and direction of linear association",
                    "prerequisites": "Normally distributed, linear relationship",
                },
                {
                    "test": "Spearman Rank Correlation",
                    "variables": [numeric_cols[0], numeric_cols[1]],
                    "description": f"Monotonic relationship between **{numeric_cols[0]}** and **{numeric_cols[1]}**",
                    "when_to_use": "When data violates normality assumption",
                    "prerequisites": "Monotonic relationship",
                },
            ])

        # Paired t-test (if structure suggests pre/post)
        if len(numeric_cols) >= 2:
            recommendations.append({
                "test": "Paired Samples T-Test",
                "variables": [numeric_cols[0], numeric_cols[1] if len(numeric_cols) > 1 else None],
                "description": f"Compare **{numeric_cols[0]}** and **{numeric_cols[1]}** (before/after or matched pairs)" if len(numeric_cols) > 1 else None,
                "when_to_use": "When you have paired/matched observations or before/after measurements",
                "prerequisites": "Normally distributed differences",
            })

        # Regression
        if len(numeric_cols) >= 2:
            recommendations.append({
                "test": "Linear Regression",
                "variables": [numeric_cols[0], numeric_cols[1]],
                "description": f"Predict **{numeric_cols[0]}** using **{numeric_cols[1]}** and other variables",
                "when_to_use": "Model relationships between multiple predictors and an outcome",
                "prerequisites": "Linearity, independence, homoscedasticity, normality",
            })

        return recommendations

    # â”€â”€â”€ Natural Language Insights â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def generate_insights(self, df: pd.DataFrame) -> List[str]:
        """Generate natural language insights about the data."""
        insights = []
        profile = profile_dataset(df)
        col_types = infer_column_types(df)

        # Dataset size insight
        if profile["rows"] > 10000:
            insights.append(f"ðŸ“ Large dataset: **{profile['rows']:,}** rows  consider using sampling for faster visualizations")
        elif profile["rows"] < 30:
            insights.append(f"ðŸ“ Small dataset: **{profile['rows']}** rows  statistical tests may have limited power")

        # Missing data insight
        if profile["missing_pct"] > 10:
            insights.append(f"â¬œ **{profile['missing_pct']}%** of cells are missing  consider imputation or removal")
        elif profile["missing_pct"] > 0:
            insights.append(f"â¬œ Minimal missing data ({profile['missing_pct']}%)  data quality is good")

        # Skewness insights
        numeric_cols = profile.get("numeric_columns", [])
        if numeric_cols:
            for col in numeric_cols[:3]:
                try:
                    skew = df[col].skew()
                    if abs(skew) > 1:
                        direction = "positively" if skew > 0 else "negatively"
                        insights.append(f" **{col}** is {direction} skewed ({skew:.2f})  consider log transformation")
                except Exception:
                    logger.warning("Skewness insight failed for column %r", col, exc_info=True)

        # Categorical insights
        cat_cols = profile.get("categorical_columns", [])
        if cat_cols:
            for col in cat_cols[:3]:
                try:
                    top_val = df[col].value_counts().index[0]
                    top_pct = df[col].value_counts().iloc[0] / len(df) * 100
                    n_unique = df[col].nunique()
                    if top_pct > 50:
                        insights.append(f"ðŸ† In **{col}**, **{top_val}** dominates ({top_pct:.0f}% of {n_unique} categories)")
                except Exception:
                    logger.warning("Categorical insight failed for column %r", col, exc_info=True)

        # Temporal insights
        temporal_cols = profile.get("temporal_columns", [])
        if temporal_cols:
            for col in temporal_cols[:1]:
                try:
                    date_range = df[col].max() - df[col].min()
                    if hasattr(date_range, 'days'):
                        insights.append(f"ðŸ“… **{col}** spans {date_range.days} days (from {df[col].min():%Y-%m-%d} to {df[col].max():%Y-%m-%d})")
                except Exception:
                    logger.warning("Temporal insight failed for column %r", col, exc_info=True)

        if not insights:
            insights.append("âœ… No notable patterns detected  data appears clean and simple")

        return insights

    # â”€â”€â”€ Visualization Recommendations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def recommend_visualizations(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate visualization suggestions based on data types."""
        from modules.viz_engine import auto_recommend_chart
        return auto_recommend_chart(df)[:8]

