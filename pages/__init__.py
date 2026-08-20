import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
"""
CHRISHEM Unified Platform — Page Registry (v9.0)
The application is organized into 11 consolidated hub pages instead of the
previous 66 individual pages. Each hub consolidates multiple tools into tabs
and shares unified infrastructure (theme, session state, navigation).

Hub pages:
  1_ðŸ _Home_Dashboard      — System overview, vault, quick access, telemetry
  2_ðŸ“_Data_Studio         — Ingestion, quality, transform, variable editor, simulator
  3_ðŸ“Š_Statistics_Studio   — Parametric/non-parametric tests, causal, Bayesian, power
  4_ðŸ¤–_ML_Predictive_Studio— AutoML, feature engineering, agents, AI cores
  5_📈_Visualization_Studio— Chart builder, dashboards, presentations, extractor
  6_ðŸ’¬_AI_NLP_Studio       — Text mining, NLP, AI insights, synthesis, gap finder
  7_ðŸ“š_Literature_Publishing_Hub — Literature, meta-analysis, APA, citations, grants
  8_ðŸ”¬_Domain_Analytics_Hub — Clinical, network, GIS, surveillance, academic, lab
  9_ðŸ”—_Integrations_Hub    — Notion, Sheets, Git, APIs, webhooks, Mendeley
  10_ðŸ›¡ï¸_Admin_Security_Center — Diagnostics, users, billing, vault, compliance
  11_ðŸ¤_Collaboration_Portfolio — Projects, pipeline, agents, team, portfolio

The original 66 pages are preserved in the `pages_archive/` directory for
reference and legacy recovery.

Unified infrastructure modules (in `modules/`):
  - theme.py           — single source of truth for UI styling
  - session_manager.py — cross-hub data state management
  - navigation.py      — role-based navigation & global command search
  - shared_ui.py       — reusable hero cards, headers, metrics, footers
  - page_bootstrap.py  — standardized page setup & sidebar rendering
"""

# Consolidated hub registry (single source of truth for file discovery).
# Keep in sync with modules/navigation.py HUBS list.
CONSOLIDATED_HUBS = [
    {"id": "home", "icon": "ðŸ ", "name": "Home Dashboard", "page": "1_ðŸ _Home_Dashboard.py"},
    {"id": "data", "icon": "ðŸ“", "name": "Data Studio", "page": "2_ðŸ“_Data_Studio.py"},
    {"id": "statistics", "icon": "ðŸ“Š", "name": "Statistics Studio", "page": "3_ðŸ“Š_Statistics_Studio.py"},
    {"id": "ml", "icon": "ðŸ¤–", "name": "ML & Predictive Studio", "page": "4_ðŸ¤–_ML_Predictive_Studio.py"},
    {"id": "visualization", "icon": "📈", "name": "Visualization Studio", "page": "5_📈_Visualization_Studio.py"},
    {"id": "nlp", "icon": "ðŸ’¬", "name": "AI & NLP Studio", "page": "6_ðŸ’¬_AI_NLP_Studio.py"},
    {"id": "literature", "icon": "ðŸ“š", "name": "Literature & Publishing Hub", "page": "7_ðŸ“š_Literature_Publishing_Hub.py"},
    {"id": "domain", "icon": "ðŸ”¬", "name": "Domain Analytics Hub", "page": "8_ðŸ”¬_Domain_Analytics_Hub.py"},
    {"id": "integrations", "icon": "ðŸ”—", "name": "Integrations Hub", "page": "9_ðŸ”—_Integrations_Hub.py"},
    {"id": "admin", "icon": "ðŸ›¡ï¸", "name": "Admin & Security Center", "page": "10_ðŸ›¡ï¸_Admin_Security_Center.py"},
    {"id": "collaboration", "icon": "ðŸ¤", "name": "Collaboration & Portfolio", "page": "11_ðŸ¤_Collaboration_Portfolio.py"},
    {"id": "forensics", "icon": "ðŸ•µï¸", "name": "Forensics Intelligence", "page": "12_ðŸ•µï¸_Forensics_Intelligence.py"},
    {"id": "converter", "icon": "ðŸ”„", "name": "Universal Converter", "page": "13_ðŸ”„_Universal_Converter.py"},
    {"id": "threat", "icon": "ðŸ›¡ï¸", "name": "Threat & Scanner Suite", "page": "14_ðŸ›¡ï¸_Threat_Scanner_Suite.py"},
    {"id": "mission", "icon": "ðŸŒ", "name": "Global Mission Control", "page": "15_ðŸŒ_Global_Mission_Control.py"},
]

PAGE_COUNT = len(CONSOLIDATED_HUBS)

__all__ = ["CONSOLIDATED_HUBS", "PAGE_COUNT"]


