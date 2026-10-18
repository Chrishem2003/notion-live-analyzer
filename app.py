"""Streamlit entry point with curated navigation.

The NEMA-AGORA pilot is intentionally presented as one workspace page.
Supporting implementation modules and historical specialist pages remain in
the repository for maintenance, but only the consolidated workspace is listed.
"""
from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
PAGES_DIR = ROOT / "pages"

home_page = st.Page("main_app.py", title="Home", default=True)
nema_page = st.Page("pages/18_NEMA_AGORA.py", title="NEMA-AGORA")

other_pages = []
if PAGES_DIR.is_dir():
    for page_path in sorted(PAGES_DIR.glob("*.py")):
        # Keep all NEMA-AGORA workflows behind their single consolidated page.
        if "NEMA_AGORA" in page_path.name.upper():
            continue
        stem = re.sub(r"^\d+_", "", page_path.stem)
        title = stem.replace("_", " ").strip() or page_path.stem
        other_pages.append(st.Page(str(page_path.relative_to(ROOT)), title=title))

navigation = {
    "Home": [home_page],
    "Environmental governance": [nema_page],
}
if other_pages:
    navigation["Other tools"] = other_pages

selected_page = st.navigation(navigation)
selected_page.run()
