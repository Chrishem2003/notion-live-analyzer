
"""Unit tests for modules.data_quality."""
import numpy as np
import pandas as pd
import pytest

from modules.data_quality import DataQualityReport
from tests.helpers import object_series


@pytest.fixture
def clean_df():
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        {
            "value": rng.normal(size=50),
            "other": rng.normal(size=50),
            "label": object_series([f"row-{i}" for i in range(50)]),
        }
    )


class TestOverview:
    def test_reports_shape_and_dtypes(self, clean_df):
        overview = DataQualityReport(clean_df, "demo").assess_overview()
        assert overview["rows"] == 50
        assert overview["columns"] == 3
        assert overview["column_names"] == ["value", "other", "label"]
        assert set(overview["dtypes"]) == {"value", "other", "label"}
        assert overview["score"] == 100


class TestCompleteness:
    def test_perfect_completeness(self, clean_df):
        result = DataQualityReport(clean_df).assess_completeness()
        assert result["missing_cells"] == 0
        assert result["score"] == 100
        assert result["issues"] == []

    def test_critical_missing_rate(self):
        df = pd.DataFrame({"a": [np.nan] * 8 + [1.0, 2.0]})
        result = DataQualityReport(df).assess_completeness()
        assert result["missing_pct"] == 80.0
        assert result["score"] == 0
        assert any("Critical" in issue for issue in result["issues"])
        assert result["cols_high_missing"] == ["a"]

    def test_warning_missing_rate(self):
        df = pd.DataFrame({"a": [np.nan] + [1.0] * 5})
        result = DataQualityReport(df).assess_completeness()
        assert 10 < result["missing_pct"] <= 20
        assert any("Warning" in issue for issue in result["issues"])

    def test_low_missing_rate_only_recommends(self):
        df = pd.DataFrame({"a": [np.nan] + [1.0] * 49, "b": list(range(50))})
        result = DataQualityReport(df).assess_completeness()
        assert result["issues"] == []
        assert result["recommendations"]

    def test_empty_dataframe_has_no_missing_pct(self):
        result = DataQualityReport(pd.DataFrame()).assess_completeness()
        assert result["missing_pct"] == 0


class TestUniqueness:
    def test_no_duplicates(self, clean_df):
        result = DataQualityReport(clean_df).assess_uniqueness()
        assert result["duplicate_rows"] == 0
        assert result["score"] == 100

    def test_critical_duplicate_rate(self):
        df = pd.DataFrame({"a": [1] * 10})
        result = DataQualityReport(df).assess_uniqueness()
        assert result["duplicate_rows"] == 9
        assert any("Critical" in issue for issue in result["issues"])

    def test_moderate_duplicate_rate(self):
        df = pd.DataFrame({"a": list(range(19)) + [18]})
        result = DataQualityReport(df).assess_uniqueness()
        assert result["duplicate_pct"] == 5.0
        assert result["issues"] == []

    def test_flags_low_and_high_cardinality_columns(self):
        df = pd.DataFrame(
            {
                "const": [1] * 200,
                "ids": object_series([f"id-{i}" for i in range(200)]),
            }
        )
        result = DataQualityReport(df).assess_uniqueness()
        assert "const" in result["low_cardinality_cols"]
        assert any("Low cardinality" in r for r in result["recommendations"])


class TestConsistency:
    def test_clean_data_scores_full(self, clean_df):
        result = DataQualityReport(clean_df).assess_consistency()
        assert result["mixed_type_columns"] == []
        assert result["score"] == 100

    def test_detects_mixed_numeric_strings(self):
        df = pd.DataFrame({"mixed": object_series(["1", "2", "3", "n/a", "4", "oops"])})
        result = DataQualityReport(df).assess_consistency()
        assert result["mixed_type_columns"] == ["mixed"]
        assert result["score"] == 90
        assert any("Mixed types" in issue for issue in result["issues"])

    def test_detects_whitespace_in_categoricals(self):
        df = pd.DataFrame({"cat": object_series([" a", "b", "a ", "b"])})
        result = DataQualityReport(df).assess_consistency()
        assert result["whitespace_issues"] == ["cat"]
        assert any("Whitespace" in issue for issue in result["issues"])


class TestValidity:
    def test_no_numeric_columns_scores_full(self):
        df = pd.DataFrame({"label": object_series(["a", "b"])})
        result = DataQualityReport(df).assess_validity()
        assert result["score"] == 100
        assert result["columns_with_outliers"] == []

    def test_detects_extreme_values(self):
        df = pd.DataFrame({"v": [1.0] * 30 + [10_000.0]})
        result = DataQualityReport(df).assess_validity()
        assert result["columns_with_outliers"] == ["v"]
        details = result["outlier_details"]["v"]
        assert details["count"] == 1
        assert details["max_val"] == 10_000.0

    def test_flags_negative_values_in_count_columns(self):
        df = pd.DataFrame({"age": [-1, 20, 30, 40]})
        result = DataQualityReport(df).assess_validity()
        assert any("negative values" in issue for issue in result["issues"])

    def test_all_nan_numeric_column_is_skipped(self):
        df = pd.DataFrame({"v": [np.nan, np.nan]})
        result = DataQualityReport(df).assess_validity()
        assert result["outlier_details"] == {}


class TestAccuracy:
    def test_detects_perfectly_correlated_columns(self):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [2.0, 4.0, 6.0, 8.0]})
        result = DataQualityReport(df).assess_accuracy()
        assert result["duplicate_columns"] == ["a≈b"]
        assert result["score"] == 85

    def test_detects_constant_and_empty_columns(self):
        df = pd.DataFrame({"const": [1, 1, 1], "empty": [np.nan, np.nan, np.nan]})
        result = DataQualityReport(df).assess_accuracy()
        assert "const" in result["constant_columns"]
        assert result["all_nan_columns"] == ["empty"]
        assert result["score"] < 100

    def test_clean_data_has_no_accuracy_issues(self, clean_df):
        result = DataQualityReport(clean_df).assess_accuracy()
        assert result["issues"] == []
        assert result["score"] == 100


class TestTimeliness:
    def test_no_date_columns_defaults_to_half_score(self, clean_df):
        result = DataQualityReport(clean_df).assess_timeliness()
        assert result["date_columns"] == []
        assert result["score"] == 50
        assert result["recommendations"]

    def test_recent_dates_score_full(self):
        dates = pd.date_range(pd.Timestamp.now().normalize() - pd.Timedelta(days=5), periods=6)
        result = DataQualityReport(pd.DataFrame({"when": dates})).assess_timeliness()
        assert result["date_columns"] == ["when"]
        assert result["score"] == 100
        assert result["when_range_days"] == 5

    def test_stale_dates_are_flagged(self):
        dates = pd.to_datetime(["2000-01-01", "2000-06-01"])
        result = DataQualityReport(pd.DataFrame({"when": dates})).assess_timeliness()
        assert result["score"] == 40
        assert any("days old" in issue for issue in result["issues"])

    def test_month_old_data_scores_seventy(self):
        end = pd.Timestamp.now().normalize() - pd.Timedelta(days=60)
        dates = pd.date_range(end - pd.Timedelta(days=10), periods=11)
        result = DataQualityReport(pd.DataFrame({"when": dates})).assess_timeliness()
        assert result["score"] == 70


class TestFullAssessment:
    def test_report_structure_and_weighted_score(self, clean_df):
        report = DataQualityReport(clean_df).run_full_assessment()
        for key in (
            "overview",
            "completeness",
            "uniqueness",
            "consistency",
            "validity",
            "accuracy",
            "timeliness",
            "overall_score",
            "issues",
            "recommendations",
        ):
            assert key in report
        assert 0 <= report["overall_score"] <= 100

    def test_overall_score_is_the_weighted_mean_of_dimensions(self, clean_df):
        report = DataQualityReport(clean_df).run_full_assessment()
        dimensions = ["completeness", "uniqueness", "consistency", "validity", "accuracy"]
        weighted = sum(report[d]["score"] * report[d]["weight"] for d in dimensions)
        total_weight = sum(report[d]["weight"] for d in dimensions)
        assert report["overall_score"] == pytest.approx(round(weighted / total_weight, 1))

    def test_issues_are_aggregated_across_dimensions(self):
        df = pd.DataFrame({"a": [np.nan] * 8 + [1.0, 1.0], "const": [1] * 10})
        report = DataQualityReport(df).run_full_assessment()
        assert report["issues"]
        assert report["recommendations"]
        assert report["overall_score"] < 100

