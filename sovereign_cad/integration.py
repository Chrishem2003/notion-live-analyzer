"""
Sovereign CAD application integration.

This module is the entry point used by the main Streamlit application.
It launches the real Sovereign CAD workspace.
"""

from __future__ import annotations

from sovereign_cad.streamlit.workspace import render_workspace


def render_cad_workspace() -> None:
    """
    Render the Sovereign CAD application.
    """

    render_workspace()