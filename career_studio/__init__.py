"""Sovereign Career Studio public package."""

def render_career_studio(*args, **kwargs):
    from .streamlit import render_career_studio as _render
    return _render(*args, **kwargs)
