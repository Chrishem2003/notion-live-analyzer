
"""Cross-version pandas helpers.

pandas 3 infers a dedicated ``str`` dtype for text columns that used to land on
``object``, so ``series.dtype == object`` no longer identifies text data.
"""
from __future__ import annotations

from typing import List

import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype


def is_text_dtype(series: pd.Series) -> bool:
    """True for text-like columns on both pandas 2 (object) and pandas 3 (str)."""
    return bool(is_object_dtype(series) or is_string_dtype(series))


def text_columns(df: pd.DataFrame) -> List[str]:
    """Names of the text-like columns, replacing ``select_dtypes(include='object')``."""
    return [col for col in df.columns if is_text_dtype(df[col])]
