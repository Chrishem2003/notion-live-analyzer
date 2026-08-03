
"""Test helpers shared across test modules."""
import pandas as pd


def object_series(values):
    """Build a text Series with ``object`` dtype.

    pandas 3 infers a dedicated ``str`` dtype for text columns while the
    application code branches on ``dtype == object``; forcing ``object`` keeps
    the tests deterministic across pandas versions.
    """
    return pd.Series(values, dtype=object)
