
"""Unit tests for modules.data_processor."""
import numpy as np
import pandas as pd
import pytest

from modules import data_processor as dp
from tests.helpers import object_series


class TestInferColumnType:
    def test_empty_series_is_unknown(self):
        assert dp.infer_column_type(pd.Series([np.nan, np.nan], dtype=float)) == "unknown"

    def test_integer_and_float(self):
        assert dp.infer_column_type(pd.Series([1, 2, 3])) == "integer"
        assert dp.infer_column_type(pd.Series([1.5, 2.5, 3.5])) == "numeric"

    def test_boolean(self):
        assert dp.infer_column_type(pd.Series([True, False, True])) == "boolean"

    def test_temporal(self):
        series = pd.Series(pd.date_range("2024-01-01", periods=5))
        assert dp.infer_column_type(series) == "temporal"

    def test_categorical_for_repeated_values(self):
        series = object_series(["a", "b"] * 60)
        assert dp.infer_column_type(series) == "categorical"

    def test_text_for_long_strings(self):
        series = object_series(["x" * 80 + str(i) for i in range(200)])
        assert dp.infer_column_type(series) == "text"

    def test_string_for_short_high_cardinality_values(self):
        series = object_series([f"id-{i}" for i in range(200)])
        assert dp.infer_column_type(series) == "string"

    def test_infer_column_types_maps_every_column(self, sample_df):
        types = dp.infer_column_types(sample_df)
        assert types == {
            "count": "integer",
            "score": "numeric",
            "flag": "boolean",
            "group": "string",
            "when": "temporal",
        }


class TestColumnSummary:
    def test_numeric_summary_includes_distribution_stats(self, sample_df):
        summary = dp.get_column_summary(sample_df, "score")
        assert summary["name"] == "score"
        assert summary["type"] == "numeric"
        assert summary["non_null_count"] == 8
        assert summary["null_count"] == 0
        assert summary["mean"] == pytest.approx(5.0)
        assert summary["median"] == pytest.approx(5.0)
        assert summary["min"] == pytest.approx(1.5)
        assert summary["max"] == pytest.approx(8.5)
        assert summary["iqr"] == pytest.approx(summary["q3"] - summary["q1"])

    def test_temporal_summary_reports_range(self, sample_df):
        summary = dp.get_column_summary(sample_df, "when")
        assert summary["type"] == "temporal"
        assert summary["range_days"] == 7

    def test_categorical_summary_reports_top_value(self, sample_df):
        summary = dp.get_column_summary(sample_df, "group")
        assert summary["type"] == "string"
        assert summary["top_value"] in {"a", "b"}
        assert summary["top_freq"] == 4
        assert summary["unique_count"] == 2

    def test_null_counts(self, missing_df):
        summary = dp.get_column_summary(missing_df, "value")
        assert summary["null_count"] == 2
        assert summary["null_pct"] == pytest.approx(33.33, abs=0.01)


class TestProfileDataset:
    def test_profile_reports_shape_and_column_groups(self, sample_df):
        profile = dp.profile_dataset(sample_df)
        assert profile["rows"] == 8
        assert profile["columns"] == 5
        assert profile["missing_cells"] == 0
        assert profile["duplicate_rows"] == 0
        assert set(profile["numeric_columns"]) == {"count", "score"}
        assert profile["categorical_columns"] == ["group"]
        assert profile["type_distribution"]["string"] == 1
        assert profile["temporal_columns"] == ["when"]
        assert profile["boolean_columns"] == ["flag"]

    def test_profile_counts_missing_and_duplicates(self, missing_df):
        profile = dp.profile_dataset(missing_df)
        assert profile["missing_cells"] == 3
        assert profile["missing_pct"] > 0


class TestCleanDataframe:
    def test_defaults_remove_duplicates_and_fill_na(self):
        df = pd.DataFrame({"n": [1.0, np.nan, 1.0], "s": ["  a  ", "b", "  a  "]})
        cleaned = dp.clean_dataframe(df)
        assert cleaned["n"].isna().sum() == 0
        assert list(cleaned["s"]) == ["a", "b"]

    def test_does_not_mutate_input(self):
        df = pd.DataFrame({"n": [1.0, np.nan]})
        dp.clean_dataframe(df)
        assert df["n"].isna().sum() == 1

    def test_fill_numeric_na_median(self):
        df = pd.DataFrame({"n": [1.0, 2.0, 60.0, np.nan]})
        cleaned = dp.clean_dataframe(
            df, {"fill_numeric_na": "median", "remove_duplicates": False}
        )
        assert cleaned["n"].iloc[-1] == pytest.approx(2.0)

    def test_fill_numeric_na_zero(self):
        df = pd.DataFrame({"n": [1.0, np.nan]})
        cleaned = dp.clean_dataframe(df, {"fill_numeric_na": "zero"})
        assert cleaned["n"].iloc[-1] == 0.0

    def test_fill_categorical_na_mode(self):
        df = pd.DataFrame({"s": ["a", "a", "b", None]})
        cleaned = dp.clean_dataframe(
            df, {"fill_categorical_na": "mode", "strip_whitespace": False}
        )
        assert cleaned["s"].isna().sum() == 0


class TestAggregation:
    def test_groupby_aggregate(self, sample_df):
        out = dp.groupby_aggregate(sample_df, ["group"], "score", "sum")
        assert set(out.columns) == {"group", "score"}
        assert out.loc[out["group"] == "a", "score"].iloc[0] == pytest.approx(1.5 + 3.5 + 5.5 + 7.5)

    def test_groupby_aggregate_falls_back_to_mean_for_invalid_func(self, sample_df):
        out = dp.groupby_aggregate(sample_df, ["group"], "score", "not-a-func")
        expected = dp.groupby_aggregate(sample_df, ["group"], "score", "mean")
        pd.testing.assert_frame_equal(out, expected)

    def test_pivot_table(self, sample_df):
        out = dp.pivot_table(sample_df, ["group"], "flag", "score", "mean")
        assert "group" in out.columns
        assert len(out) == 2

    @pytest.mark.parametrize("agg_func", ["mean", "sum", "std"])
    def test_rolling_aggregate_adds_column(self, sample_df, agg_func):
        out = dp.rolling_aggregate(sample_df, "when", "score", window=3, agg_func=agg_func)
        assert f"rolling_{agg_func}_3" in out.columns
        assert len(out) == len(sample_df)

    def test_rolling_aggregate_sorts_by_date(self):
        df = pd.DataFrame(
            {
                "when": pd.to_datetime(["2024-01-03", "2024-01-01", "2024-01-02"]),
                "score": [3.0, 1.0, 2.0],
            }
        )
        out = dp.rolling_aggregate(df, "when", "score", window=2)
        assert list(out["score"]) == [1.0, 2.0, 3.0]
        assert out["rolling_mean_2"].iloc[-1] == pytest.approx(2.5)


class TestOutliers:
    def test_detect_outliers_iqr(self):
        df = pd.DataFrame({"n": [1, 2, 3, 4, 5, 1000]})
        flags = dp.detect_outliers_iqr(df, "n")
        assert flags.iloc[-1]
        assert not flags.iloc[:-1].any()

    def test_detect_outliers_zscore(self):
        df = pd.DataFrame({"n": [10.0] * 30 + [500.0]})
        flags = dp.detect_outliers_zscore(df, "n", threshold=3.0)
        assert flags.sum() <= 1

    def test_detect_outliers_zscore_constant_column(self):
        df = pd.DataFrame({"n": [5.0, 5.0, 5.0]})
        flags = dp.detect_outliers_zscore(df, "n")
        assert not flags.any()


class TestBinning:
    def test_bin_column_uniform(self, sample_df):
        binned = dp.bin_column(sample_df, "score", bins=2, labels=["low", "high"])
        assert set(binned.dropna().unique()) == {"low", "high"}

    def test_bin_column_quantile(self, sample_df):
        binned = dp.bin_column_quantile(sample_df, "score", q=4)
        assert binned.nunique() == 4


class _FakeContext:
    def __init__(self):
        self.captured = []

    def capture(self, before, after):
        self.captured.append((before, after))


class _FakeTracker:
    """Minimal stand-in for ProvenanceTracker."""

    def __init__(self):
        self.operations = []
        self.contexts = []

    def track(self, name, operation_desc="", parameters=None):
        self.operations.append((name, operation_desc, parameters))
        ctx = _FakeContext()
        self.contexts.append(ctx)

        class _CM:
            def __enter__(_self):
                return ctx

            def __exit__(_self, *exc):
                return False

        return _CM()


class TestTrackedWrappers:
    @pytest.fixture
    def tracker(self):
        return _FakeTracker()

    def test_tracked_functions_passthrough_without_tracker(self, sample_df):
        pd.testing.assert_frame_equal(
            dp.tracked_clean_dataframe(sample_df, None),
            dp.clean_dataframe(sample_df),
        )
        pd.testing.assert_frame_equal(
            dp.tracked_groupby_aggregate(sample_df, None, ["group"], "score"),
            dp.groupby_aggregate(sample_df, ["group"], "score"),
        )
        pd.testing.assert_frame_equal(
            dp.tracked_pivot_table(sample_df, None, ["group"], "flag", "score"),
            dp.pivot_table(sample_df, ["group"], "flag", "score"),
        )
        pd.testing.assert_frame_equal(
            dp.tracked_rolling_aggregate(sample_df, None, "when", "score"),
            dp.rolling_aggregate(sample_df, "when", "score"),
        )
        pd.testing.assert_series_equal(
            dp.tracked_bin_column(sample_df, None, "score", bins=2),
            dp.bin_column(sample_df, "score", bins=2),
        )

    def test_tracked_clean_dataframe_records_operation(self, sample_df, tracker):
        dp.tracked_clean_dataframe(sample_df, tracker)
        assert tracker.operations[0][0] == "clean_dataframe"
        assert len(tracker.contexts[0].captured) == 1

    def test_tracked_groupby_aggregate_records_parameters(self, sample_df, tracker):
        dp.tracked_groupby_aggregate(sample_df, tracker, ["group"], "score", "sum")
        name, _desc, params = tracker.operations[0]
        assert name == "groupby_aggregate"
        assert params == {"group_cols": ["group"], "agg_col": "score", "agg_func": "sum"}

    def test_tracked_pivot_table_records_operation(self, sample_df, tracker):
        dp.tracked_pivot_table(sample_df, tracker, ["group"], "flag", "score")
        assert tracker.operations[0][0] == "pivot_table"

    def test_tracked_rolling_aggregate_records_operation(self, sample_df, tracker):
        result = dp.tracked_rolling_aggregate(sample_df, tracker, "when", "score", window=2)
        assert tracker.operations[0][0] == "rolling_aggregate"
        assert "rolling_mean_2" in result.columns

    def test_tracked_bin_column_records_operation(self, sample_df, tracker):
        result = dp.tracked_bin_column(sample_df, tracker, "score", bins=2)
        assert tracker.operations[0][0] == "bin_column"
        assert len(result) == len(sample_df)


class TestGetTrackerFromSession:
    def test_creates_and_reuses_tracker(self, bare_session_state):
        tracker = dp.get_tracker_from_session()
        assert bare_session_state["_provenance_tracker"] is tracker
        assert dp.get_tracker_from_session() is tracker

