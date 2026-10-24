"""Functional Streamlit gate test for the NEMA console's unauthenticated path."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_console_stops_before_rendering_case_data_without_portal_session():
    repo_root = Path(__file__).resolve().parents[1]
    page_path = repo_root / "pages" / "18_NEMA_AGORA_Case_Console.py"
    app = AppTest.from_file(page_path, default_timeout=15).run()

    warnings = [element.value for element in app.warning]
    assert any(
        "Sign in through the main CHRISHEM portal" in value
        for value in warnings
    )
    # The guard must stop execution before storage readiness or case data render.
    assert len(app.metric) == 0
    assert len(app.subheader) == 0
    assert len(app.exception) == 0
