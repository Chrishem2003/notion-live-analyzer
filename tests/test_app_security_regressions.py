"""Regression guards for authentication and embedded workspace security fixes.

These lightweight source-level tests protect the high-risk wiring in the single-file
Streamlit entrypoint without importing the full UI or initializing production state.
"""
from pathlib import Path


APP_SOURCE = Path(__file__).resolve().parents[1] / "app.py"


def test_legacy_email_cookie_never_authenticates_a_session():
    source = APP_SOURCE.read_text(encoding="utf-8")

    # An email string is an identifier, not an authentication credential.
    assert 'saved_email = cookie_manager.get(cookie="chrishem_user_email")' not in source
    assert 'cookie_manager.set("chrishem_user_email"' not in source
    assert "Do not restore authentication from the legacy" in source
    assert "if not st.session_state.portal_unlocked:" in source


def test_notion_preview_uses_supported_streamlit_iframe_api():
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "st.iframe(NOTION_EMBED_URL" in source
    assert "st.components.v1.iframe(" not in source
