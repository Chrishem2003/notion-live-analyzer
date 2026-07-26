"""Unit tests for modules.pandas_compat and its use across the app."""
import pandas as pd

from modules.data_processor import infer_column_type
from modules.data_quality import DataQualityReport
from modules.pandas_compat import is_text_dtype

from tests.helpers import object_series


class TestIsTextDtype:
    def test_object_dtype_text(self):
        assert is_text_dtype(object_series(["a", "b"])) is True

    def test_inferred_text_dtype(self):
        # pandas 3 infers `str`; pandas 2 keeps `object` — both are text.
        assert is_text_dtype(pd.Series(["a", "b"])) is True

    def test_numeric_strings_are_text(self):
        assert is_text_dtype(pd.Series(["1", "2"])) is True

    def test_numeric_dtype_is_not_text(self):
        assert is_text_dtype(pd.Series([1, 2, 3])) is False

    def test_datetime_dtype_is_not_text(self):
        assert is_text_dtype(pd.Series(pd.date_range("2024-01-01", periods=3))) is False

    def test_object_dtype_non_text_still_counts(self):
        # Mixed object columns kept the old `dtype == object` behaviour.
        assert is_text_dtype(pd.Series([{"a": 1}, {"b": 2}])) is True


class TestInferenceWithoutObjectDtype:
    """Regression: text inference must not depend on the `object` dtype."""

    def test_long_strings_infer_as_text(self):
        series = pd.Series([f"{'x' * 60}-{i}" for i in range(40)])
        assert infer_column_type(series) == "text"

    def test_short_unique_strings_infer_as_string(self):
        series = pd.Series([f"code-{i}" for i in range(40)])
        assert infer_column_type(series) == "string"


class TestDataQualityWithoutObjectDtype:
    def test_mixed_numeric_strings_detected(self):
        df = pd.DataFrame({"mixed": ["1", "2", "3", "4", "5", "6", "x", "y", "z", "w"]})
        result = DataQualityReport(df).assess_consistency()
        assert result["mixed_type_columns"] == ["mixed"]

    def test_unique_strings_flagged_as_high_cardinality(self):
        df = pd.DataFrame({"id": [f"id-{i}" for i in range(200)]})
        result = DataQualityReport(df).assess_uniqueness()
        assert "id" in result["high_cardinality_cols"]
