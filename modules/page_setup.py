"""
Page Setup — shared bootstrap helpers for the Streamlit pages in `pages/`.

Every page repeats the same three concerns: initialising session state and
theme, resolving the dataset the user is working on, and gating the page on an
optional dependency. These helpers centralise that logic.
"""
from importlib import import_module
from typing import Optional

import pandas as pd
import streamlit as st

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark

WATERMARK_TEXT = "CHRISHEM"
NO_DATA_WARNING = "⚠️ No data available. Load data first."


def is_dark_theme() -> bool:
    """Whether the user selected the dark theme."""
    return st.session_state.get("theme", "light") == "dark"


def bootstrap_page(
    title: str,
    subtitle: str,
    badge_text: Optional[str] = None,
    is_dark: Optional[bool] = None,
) -> None:
    """Initialise session state, inject the theme CSS, and render the page header."""
    init_session_state()
    load_css(is_dark=is_dark_theme() if is_dark is None else is_dark)
    hero_card(title, subtitle, badge_text)
    watermark(WATERMARK_TEXT)


def get_active_dataframe(
    required: bool = True,
    warning: str = NO_DATA_WARNING,
) -> Optional[pd.DataFrame]:
    """Return the active dataset, falling back to the Notion-synced dataset.

    When `required` is set and no data is loaded, the warning is shown and the
    page execution stops.
    """
    for key in ("active_df", "notion_df"):
        df = st.session_state.get(key)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df

    if required:
        st.warning(warning)
        st.stop()
    return None


def require_dependency(module_name: str, message: str, stop: bool = True) -> bool:
    """Check that an optional dependency is importable.

    Renders `message` when the dependency is missing — as an error that halts
    the page when `stop` is set, otherwise as a warning about degraded
    functionality. Returns whether the dependency is available.
    """
    try:
        import_module(module_name)
    except ImportError:
        if stop:
            st.error(message)
            st.stop()
        st.warning(message)
        return False
    return True
