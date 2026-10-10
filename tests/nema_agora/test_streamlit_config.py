"""Regression checks for Streamlit server configuration."""
from pathlib import Path


def test_cross_origin_protection_is_not_disabled():
    config = (Path(__file__).resolve().parents[2] / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "enableCORS = false" not in config


def test_xsrf_protection_is_enabled():
    config = (Path(__file__).resolve().parents[2] / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "enableXsrfProtection = true" in config
