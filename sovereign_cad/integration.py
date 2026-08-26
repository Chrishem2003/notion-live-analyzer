"""
Sovereign CAD Streamlit Integration Layer.

This module is the single entry point used by the main Chrishem
Science Hub application to render the Sovereign CAD workspace.
"""

from __future__ import annotations

import traceback

import streamlit as st


def render_cad_workspace() -> None:
    """
    Render the Sovereign CAD workspace.

    The CAD engine is isolated so that a CAD-specific error does not
    crash the entire Chrishem Science Hub application.
    """

    try:
        from sovereign_cad.streamlit.workspace import (
            render_cad_workspace as render_workspace,
        )

        render_workspace()

    except Exception as exc:

        st.error(
            "❌ Sovereign CAD workspace failed to load."
        )

        st.error(
            f"{type(exc).__name__}: {exc}"
        )

        with st.expander(
            "Show Sovereign CAD technical traceback"
        ):
            st.code(
                traceback.format_exc(),
                language="text",
            )