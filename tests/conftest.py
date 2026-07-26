"""Shared fixtures for the unit test suite."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from tests.helpers import object_series  # noqa: E402


@pytest.fixture
def sample_df():
    """A small mixed-type DataFrame covering every inferred column type."""
    return pd.DataFrame(
        {
            "count": [1, 2, 3, 4, 5, 6, 7, 8],
            "score": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5],
            "flag": [True, False, True, False, True, False, True, False],
            "group": object_series(["a", "b", "a", "b", "a", "b", "a", "b"]),
            "when": pd.date_range("2024-01-01", periods=8, freq="D"),
        }
    )


@pytest.fixture
def missing_df():
    """A DataFrame with missing values, duplicates and a constant column."""
    return pd.DataFrame(
        {
            "value": [1.0, 2.0, np.nan, 2.0, np.nan, 6.0],
            "label": object_series(["x", "y", None, "y", "z", "z"]),
            "constant": [7, 7, 7, 7, 7, 7],
        }
    )


@pytest.fixture
def bare_session_state(monkeypatch):
    """Replace ``st.session_state`` with a plain dict for the duration of a test."""
    import streamlit as st

    state: dict = {}
    monkeypatch.setattr(st, "session_state", state, raising=False)
    return state
