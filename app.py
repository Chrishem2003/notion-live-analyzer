"""Curated Streamlit entry point with one NEMA-AGORA workspace."""
from __future__ import annotations

from pathlib import Path
import streamlit as st

from app_navigation import discover_other_pages

ROOT = Path(__file__).resolve().parent
PAGES_DIR = ROOT / "pages"

home_page = st.Page("main_app.py", title="Home", default=True)
nema_page = st.Page("pages/18_NEMA_AGORA.py", title="NEMA-AGORA")
other_pages = [
    st.Page(path, title=title)
    for path, title in discover_other_pages(ROOT, PAGES_DIR)
]

navigation = {
    "Home": [home_page],
    "Environmental governance": [nema_page],
}
if other_pages:
    navigation["Other tools"] = other_pages

selected_page = st.navigation(navigation)
selected_page.run()
