"""Tests for shared test data helpers."""

from tests.helpers import object_series


def test_object_series_preserves_object_dtype_and_missing_values():
    series = object_series(["alpha", None, 3])

    assert str(series.dtype) == "object"
    assert series.iloc[0] == "alpha"
    assert series.iloc[1] is None
    assert series.iloc[2] == 3


def test_object_series_supports_empty_input():
    series = object_series([])

    assert str(series.dtype) == "object"
    assert series.empty
