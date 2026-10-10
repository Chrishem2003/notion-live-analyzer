"""Regression tests for Streamlit cross-origin and XSRF configuration."""
from pathlib import Path
import re


def test_cross_origin_protection_is_not_explicitly_disabled():
    config = (Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert not re.search(r"(?im)^\s*enableCORS\s*=\s*false\s*(?:#.*)?$", config)


def test_xsrf_protection_is_enabled():
    config = (Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert re.search(r"(?im)^\s*enableXsrfProtection\s*=\s*true\s*(?:#.*)?$", config)
