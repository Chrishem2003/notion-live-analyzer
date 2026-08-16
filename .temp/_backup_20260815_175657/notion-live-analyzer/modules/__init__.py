
"""
CHRISHEM Research Data Analyzer & Visualizer  Module Package
A world-class research tool that replaces SPSS, STATA, Tableau, Power BI, and more.
"""

__version__ = "3.1.0"
__author__ = "CHRISHEM"

# ── Enterprise module exports (lazy-safe) ──────────────────────────────
_enterprise_modules = [
    "llm_router",
    "self_correcting_executor",
    "mendeley_integration",
    "gis_engine",
    "spss_suite",
    "task_status_registry",
]

for _mod in _enterprise_modules:
    try:
        __import__(f"modules.{_mod}")
    except Exception:
        pass

