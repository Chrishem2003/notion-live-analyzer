import security_guard
import security_guard

"""
Data Quality Module  automated data quality assessment, reporting, and improvement suggestions.
Like SPSS Data Audit and Quality Assurance.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np
import streamlit as st
import warnings
from datetime import datetime

from modules.pandas_compat import is_text_dtype, text_columns


class DataQualityReport:
    """Comprehensive data quality assessment engine."""

    def __init__(self, df: pd.DataFrame, name: str = "Dataset"):
        self.df = df
        self.name = name
        self.report = {}

    def run_full_assessment(self) -> Dict[str, Any]:
        """Run all quality checks and return comprehensive report."""
        self.report = {
            "overview": self.assess_overview(),
            "completeness": self.assess_completeness(),
            "uniqueness": self.assess_uniqueness(),
            "consistency": self.assess_consistency(),
            "validity": self.assess_validity(),
            "accuracy": self.assess_accuracy(),
            "timeliness": self.assess_timeliness(),
            "overall_score": 0,
            "issues": [],
            "recommendations": [],
        }

        # Calculate overall score
        scores = []
        dimensions = ["completeness", "uniqueness", "consistency", "validity", "accuracy"]
        for dim in dimensions:
            if dim in self.report:
                dim_score = self.report[dim].get("score", 0)
                dim_weight = self.report[dim].get("weight", 1)
                scores.append(dim_score * dim_weight)

        overall = sum(scores) / sum(
            self.report[dim].get("weight", 1) for dim in dimensions if dim in self.report
        ) if scores else 0
        self.report["overall_score"] = round(overall, 1)

        # Aggregate issues
        for dim in dimensions:
            if dim in self.report:
                self.report["issues"].extend(self.report[dim].get("issues", []))
                self.report["recommendations"].extend(self.report[dim].get("recommendations", []))

        return self.report

    def assess_overview(self) -> Dict[str, Any]:
        """Basic dataset overview."""
        return {
            "rows": len(self.df),
            "columns": len(self.df.columns),
            "column_names": self.df.columns.tolist(),
            "dtypes": {str(k): str(v) for k, v in self.df.dtypes.items()},
            "memory_mb": round(self.df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
            "score": 100,
            "weight": 1,
        }

    def assess_completeness(self) -> Dict[str, Any]:
        """Assess missing value completeness."""
        total_cells = self.df.shape[0] * self.df.shape[1]
        missing_cells = int(self.df.isna().sum().sum())
        missing_pct = round(missing_cells / total_cells * 100, 2) if total_cells > 0 else 0

        col_missing = self.df.isna().sum()
        cols_with_missing = col_missing[col_missing > 0].sort_values(ascending=False)

        # Score: 100 - (missing_pct * 2)
        score = max(0, 100 - missing_pct * 2)

        issues = []
        recommendations = []
        if missing_pct > 20:
            issues.append(f"Critical: {missing_pct}% of all cells are missing")
            recommendations.append("Consider removing columns with >50% missing values")
            recommendations.append("Use imputation (mean/median/mode) for numeric missing values")
        elif missing_pct > 10:
            issues.append(f"Warning: {missing_pct}% of cells are missing")
            recommendations.append("Investigate causes of missing data")
            recommendations.append("Consider imputation strategies")
        elif missing_pct > 0:
            recommendations.append("Low missing rate  monitor for future increases")

        # Flag columns with high missing
        high_missing = col_missing[col_missing / len(self.df) > 0.3]
        if len(high_missing) > 0:
            for col in high_missing.index:
                pct = high_missing[col] / len(self.df) * 100
                issues.append(f"Column '{col}' has {pct:.1f}% missing values")
                recommendations.append(f"Consider dropping or imputing '{col}'")

        return {
            "missing_cells": missing_cells,
            "missing_pct": missing_pct,
            "complete_cells": total_cells - missing_cells,
            "columns_with_missing": len(cols_with_missing),
            "cols_high_missing": high_missing.index.tolist() if len(high_missing) > 0 else [],
            "score": round(score, 1),
            "weight": 5,
            "issues": issues,
            "recommendations": recommendations,
        }

    def assess_uniqueness(self) -> Dict[str, Any]:
        """Assess duplicate rows and unique value ratios."""
        duplicate_rows = self.df.duplicated().sum()
        duplicate_pct = round(duplicate_rows / len(self.df) * 100, 2) if len(self.df) > 0 else 0

        issues = []
        recommendations = []

        if duplicate_pct > 20:
            issues.append(f"Critical: {duplicate_pct}% of rows are duplicates")
            recommendations.append("Remove duplicate rows")
        elif duplicate_pct > 5:
            issues.append(f"{duplicate_pct}% of rows are duplicates")
            recommendations.append("Investigate duplicate causes (data entry errors?)")

        # Column uniqueness
        low_cardinality = []
        high_cardinality = []
        for col in self.df.columns:
            nunique = self.df[col].nunique()
            ratio = nunique / len(self.df) if len(self.df) > 0 else 0
            if ratio < 0.01 and len(self.df) > 100:
                low_cardinality.append(col)
            elif ratio > 0.99 and is_text_dtype(self.df[col]):
                high_cardinality.append(col)

        if low_cardinality:
            recommendations.append(f"Low cardinality columns (potential constants): {', '.join(low_cardinality[:5])}")
        if high_cardinality:
            recommendations.append(f"High cardinality columns (potential IDs): {', '.join(high_cardinality[:5])}")

        # Score
        score = max(0, 100 - duplicate_pct * 3)

        return {
            "duplicate_rows": int(duplicate_rows),
            "duplicate_pct": duplicate_pct,
            "low_cardinality_cols": low_cardinality[:10],
            "high_cardinality_cols": high_cardinality[:10],
            "score": round(score, 1),
            "weight": 3,
            "issues": issues,
            "recommendations": recommendations,
        }

    def assess_consistency(self) -> Dict[str, Any]:
        """Assess data type and format consistency."""
        issues = []
        recommendations = []

        # Check mixed types
        mixed_types = []
        for col in self.df.columns:
            if is_text_dtype(self.df[col]):
                # Check if column should be numeric
                numeric_vals = pd.to_numeric(self.df[col], errors='coerce')
                numeric_ratio = numeric_vals.notna().sum() / max(len(self.df), 1)
                if 0.3 < numeric_ratio < 1.0:
                    mixed_types.append(col)

        if mixed_types:
            issues.append(f"Mixed types detected: {', '.join(mixed_types[:5])}")
            recommendations.append("Clean mixed-type columns  convert to appropriate type")

        # Check date consistency
        date_issues = []
        for col in text_columns(self.df):
            try:
                with warnings.catch_warnings():
                    # Non-date text columns are expected here; the format probe is deliberate.
                    warnings.simplefilter("ignore", UserWarning)
                    parsed = pd.to_datetime(self.df[col], errors='coerce')
                if parsed.notna().sum() > 0.3 * len(self.df) and parsed.notna().sum() < len(self.df):
                    date_issues.append(col)
            except Exception:
                pass

        if date_issues:
            recommendations.append(f"Convert mixed date columns: {', '.join(date_issues[:3])}")

        # Check categorical consistency (unique values vs expected)
        cat_issues = []
        for col in text_columns(self.df):
            if self.df[col].nunique() <= 20:
                # Check for whitespace inconsistencies
                with_ws = self.df[col].str.contains(r'^\s|\s$', na=False).sum()
                if with_ws > 0:
                    cat_issues.append(col)

        if cat_issues:
            issues.append(f"Whitespace in categorical data: {', '.join(cat_issues[:5])}")
            recommendations.append("Strip whitespace from categorical columns")

        # Score
        score = 100
        if mixed_types:
            score -= 10 * len(mixed_types)
        if date_issues:
            score -= 5 * len(date_issues)
        score = max(0, score)

        return {
            "mixed_type_columns": mixed_types,
            "date_format_issues": date_issues,
            "whitespace_issues": cat_issues,
            "score": round(score, 1),
            "weight": 3,
            "issues": issues,
            "recommendations": recommendations,
        }

    def assess_validity(self) -> Dict[str, Any]:
        """Assess value validity  out-of-range, impossible values."""
        issues = []
        recommendations = []

        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        invalid_values = {}

        for col in numeric_cols:
            series = self.df[col].dropna()
            if len(series) == 0:
                continue

            # Detect impossible values using IQR
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 3 * iqr
            upper = q3  3 * iqr

            extreme = series[(series < lower) | (series > upper)]
            if len(extreme) > 0:
                invalid_values[col] = {
                    "count": len(extreme),
                    "pct": round(len(extreme) / len(series) * 100, 1),
                    "range": f"[{lower:.1f}, {upper:.1f}]",
                    "min_val": float(series.min()),
                    "max_val": float(series.max()),
                }

        if invalid_values:
            for col, info in invalid_values.items():
                issues.append(f"'{col}': {info['count']} values ({info['pct']}%) outside expected range {info['range']}")
            recommendations.append("Review extreme values  check for data entry errors")
            recommendations.append("Consider winsorizing or transforming extreme values")

        # Check for negative values where impossible
        for col in numeric_cols:
            if (self.df[col] < 0).any():
                neg_count = (self.df[col] < 0).sum()
                if "age" in col.lower() or "count" in col.lower() or "frequency" in col.lower():
                    issues.append(f"'{col}' has {neg_count} negative values (should be non-negative)")
                    recommendations.append(f"Flag or correct negative values in '{col}'")

        # Score: deduct per column with validity issues
        score = max(0, 100 - len(invalid_values) * 10 - len(numeric_cols) * 2)

        return {
            "columns_with_outliers": list(invalid_values.keys()),
            "outlier_details": invalid_values,
            "score": round(score, 1),
            "weight": 4,
            "issues": issues,
            "recommendations": recommendations,
        }

    def assess_accuracy(self) -> Dict[str, Any]:
        """Assess data accuracy through basic logical checks."""
        issues = []
        recommendations = []

        # Check for exact duplicate columns
        col_corr = self.df.select_dtypes(include=[np.number]).corr().abs()
        duplicate_cols = []
        if not col_corr.empty:
            for i in range(len(col_corr.columns)):
                for j in range(i  1, len(col_corr.columns)):
                    if col_corr.iloc[i, j] > 0.999:
                        duplicate_cols.append((col_corr.columns[i], col_corr.columns[j]))

        if duplicate_cols:
            issues.append(f"Potential duplicate columns (r > 0.999): {', '.join([f'{a}={b}' for a,b in duplicate_cols[:3]])}")
            recommendations.append("Remove or merge duplicate columns")

        # Check constant columns
        constant_cols = [col for col in self.df.columns if self.df[col].nunique() <= 1]
        if constant_cols:
            issues.append(f"Constant columns (no variance): {', '.join(constant_cols[:5])}")
            recommendations.append("Remove constant columns  they add no predictive value")

        # Check for columns with all NaN
        all_nan = [col for col in self.df.columns if self.df[col].isna().all()]
        if all_nan:
            issues.append(f"Empty columns (all NaN): {', '.join(all_nan)}")
            recommendations.append("Remove completely empty columns")

        # Score
        score = 100
        score -= 15 * len(duplicate_cols)
        score -= 10 * len(constant_cols)
        score -= 20 * len(all_nan)
        score = max(0, score)

        return {
            "duplicate_columns": [f"{a}â‰ˆ{b}" for a, b in duplicate_cols],
            "constant_columns": constant_cols,
            "all_nan_columns": all_nan,
            "score": round(score, 1),
            "weight": 3,
            "issues": issues,
            "recommendations": recommendations,
        }

    def assess_timeliness(self) -> Dict[str, Any]:
        """Assess temporal coverage and recency if date columns exist."""
        issues = []
        recommendations = []

        date_cols = []
        for col in self.df.columns:
            if pd.api.types.is_datetime64_any_dtype(self.df[col]):
                date_cols.append(col)

        result = {
            "date_columns": date_cols,
            "score": 50,  # Default if no dates
            "weight": 1,
            "issues": issues,
            "recommendations": recommendations,
        }

        if date_cols:
            for col in date_cols:
                dates = self.df[col].dropna()
                if len(dates) > 0:
                    date_range = (dates.max() - dates.min()).days
                    recency = (pd.Timestamp.now() - dates.max()).days
                    result[f"{col}_range_days"] = date_range
                    result[f"{col}_recency_days"] = recency

                    if date_range > 0:
                        result["score"] = 100
                    if recency > 365:
                        issues.append(f"Data in '{col}' is {recency} days old")
                        recommendations.append("Update data for more current analysis")
                        result["score"] = 40
                    elif recency > 30:
                        result["score"] = 70
        else:
            recommendations.append("Add date column for temporal analysis")

        return result


# â”€â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def render_data_quality_ui(df: pd.DataFrame):
    """Render the data quality dashboard."""
    st.markdown("## ðŸ” Data Quality Assessment")
    st.markdown("*Automated data quality audit  completeness, uniqueness, consistency, validity, accuracy*")

    if df is None or df.empty:
        st.warning("No data available. Load data first.")
        return

    if st.button("ðŸš€ Run Full Quality Assessment", type="primary"):
        with st.spinner("Running comprehensive data quality audit..."):
            qa = DataQualityReport(df)
            report = qa.run_full_assessment()

        # Overall Score
        overall = report.get("overall_score", 0)
        score_color = "#2ecc71" if overall >= 80 else "#e67e22" if overall >= 60 else "#e74c3c"
        score_label = "Excellent" if overall >= 90 else "Good" if overall >= 80 else \
                      "Fair" if overall >= 70 else "Poor" if overall >= 60 else "Critical"

        st.markdown(f"""
        <div style="text-align:center;padding:2rem;border-radius:18px;
                     background:linear-gradient(135deg, {score_color}20, {score_color}08);
                     border:2px solid {score_color};margin-bottom:1rem;">
            <div style="font-size:4rem;font-weight:900;color:{score_color};">{overall}</div>
            <div style="font-size:1.5rem;font-weight:700;color:{score_color};">{score_label}</div>
            <div style="font-size:0.9rem;color:#666;">Data Quality Score</div>
        </div>
        """, unsafe_allow_html=True)

        # Dimension Scores
        st.subheader(" Quality Dimensions")
        dimensions = ["completeness", "uniqueness", "consistency", "validity", "accuracy", "timeliness"]
        dim_labels = {
            "completeness": "âœ… Completeness",
            "uniqueness": "ðŸ”‘ Uniqueness",
            "consistency": "ðŸ“ Consistency",
            "validity": "âœ… Validity",
            "accuracy": "ðŸŽ¯ Accuracy",
            "timeliness": "â° Timeliness",
        }

        cols = st.columns(3)
        for i, dim in enumerate(dimensions):
            if dim in report:
                dim_data = report[dim]
                dim_score = dim_data.get("score", 0)
                dim_color = "#2ecc71" if dim_score >= 80 else "#e67e22" if dim_score >= 60 else "#e74c3c"
                with cols[i % 3]:
                    st.markdown(f"""
                    <div style="padding:0.8rem;border-radius:12px;border:1px solid {dim_color}30;background:{dim_color}08;margin:0.3rem 0;">
                        <strong>{dim_labels.get(dim, dim)}</strong><br>
                        <span style="font-size:1.5rem;font-weight:700;color:{dim_color};">{dim_score}</span>
                    </div>
                    """, unsafe_allow_html=True)

        # Issues
        issues = report.get("issues", [])
        if issues:
            st.subheader("âš ï¸ Issues Found")
            for issue in issues:
                st.warning(issue)
        else:
            st.success("âœ… No significant quality issues detected!")

        # Recommendations
        recommendations = report.get("recommendations", [])
        if recommendations:
            st.subheader("ðŸ’¡ Recommendations")
            for i, rec in enumerate(recommendations):
                insight_card("ðŸ’¡", rec)

        # Overview
        st.subheader("ðŸ“‹ Dataset Overview")
        overview = report.get("overview", {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Rows", f"{overview.get('rows', 0):,}")
        with col2:
            st.metric("Columns", overview.get("columns", 0))
        with col3:
            st.metric("Memory", f"{overview.get('memory_mb', 0)} MB")
        with col4:
            completeness = report.get("completeness", {})
            st.metric("Completeness", f"{completeness.get('missing_pct', 0)}% missing")

        # Column Quality Table
        st.subheader("ðŸ“‹ Column-by-Column Quality")
        col_quality = []
        for col in df.columns:
            n_missing = int(df[col].isna().sum())
            missing_pct = round(df[col].isna().mean() * 100, 1)
            nunique = df[col].nunique()
            dtype = str(df[col].dtype)

            if df[col].dtype in [np.number]:
                try:
                    n_outliers = len(df[col][np.abs(df[col] - df[col].mean()) > 3 * df[col].std()])
                except Exception:
                    n_outliers = 0
            else:
                n_outliers = 0

            quality = "âœ…" if missing_pct < 5 and n_outliers == 0 else \
                      "âš ï¸" if missing_pct < 30 else "âŒ"

            col_quality.append({
                "Column": col,
                "Type": dtype,
                "Quality": quality,
                "Missing %": missing_pct,
                "Unique": nunique,
                "Outliers": n_outliers,
            })

        col_quality_df = pd.DataFrame(col_quality)
        st.dataframe(col_quality_df, use_container_width=True, hide_index=True)

    else:
        st.info("ðŸ‘† Click **'Run Full Quality Assessment'** to audit your data")

        # Quick stats
        st.subheader(" Quick Dataset Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Rows", f"{len(df):,}")
        with col2:
            st.metric("Columns", len(df.columns))
        with col3:
            missing = df.isna().sum().sum()
            st.metric("Missing Cells", f"{missing:,}")
        with col4:
            dups = df.duplicated().sum()
            st.metric("Duplicates", f"{dups:,}")


def insight_card(icon: str, text: str):
    """Render an insight card."""
    st.markdown(
        f'<div class="insight-card" style="padding:0.6rem 0.8rem;margin:0.3rem 0;'
        f'border-radius:10px;border-left:4px solid #1d4ed8;background:rgba(29,78,216,0.05);">'
        f'{icon} {text}</div>',
        unsafe_allow_html=True,
    )

