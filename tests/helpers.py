"""Shared helpers for tests."""

from collections.abc import Iterable

import pandas as pd


def object_series(values: Iterable[object], *, name: str | None = None) -> pd.Series:
    """Return a Series with object dtype, preserving mixed and missing values."""
    return pd.Series(list(values), dtype=object, name=name)
