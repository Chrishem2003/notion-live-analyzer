"""
CHRISHEM Unified Platform — Page Registry (v9.0)
The application is organized into 11 consolidated hub pages instead of the
previous 66 individual pages. Each hub consolidates multiple tools into tabs
and shares unified infrastructure (theme, session state, navigation).

Hub pages:
  1_🏠_Home_Dashboard      — System overview, vault, quick access, telemetry
  2_📁_Data_Studio         — Ingestion, quality, transform, variable editor, simulator
  3_📊_Statistics_Studio   — Parametric/non-parametric tests, causal, Bayesian, power
  4_🤖_ML_Predictive_Studio— AutoML, feature engineering, agents, AI cores
  5_📈_Visualization_Studio— Chart builder, dashboards, presentations, extractor
  6_💬_AI_NLP_Studio       — Text mining, NLP, AI insights, synthesis, gap finder
  7_📚_Literature_Publishing_Hub — Literature, meta-analysis, APA, citations, grants
  8_🔬_Domain_Analytics_Hub — Clinical, network, GIS, surveillance, academic, lab
  9_🔗_Integrations_Hub    — Notion, Sheets, Git, APIs, webhooks, Mendeley
  10_🛡️_Admin_Security_Center — Diagnostics, users, billing, vault, compliance
  11_🤝_Collaboration_Portfolio — Projects, pipeline, agents, team, portfolio

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
    {"id": "home", "icon": "🏠", "name": "Home Dashboard", "page": "1_🏠_Home_Dashboard.py"},
    {"id": "data", "icon": "📁", "name": "Data Studio", "page": "2_📁_Data_Studio.py"},
    {"id": "statistics", "icon": "📊", "name": "Statistics Studio", "page": "3_📊_Statistics_Studio.py"},
    {"id": "ml", "icon": "🤖", "name": "ML & Predictive Studio", "page": "4_🤖_ML_Predictive_Studio.py"},
    {"id": "visualization", "icon": "📈", "name": "Visualization Studio", "page": "5_📈_Visualization_Studio.py"},
    {"id": "nlp", "icon": "💬", "name": "AI & NLP Studio", "page": "6_💬_AI_NLP_Studio.py"},
    {"id": "literature", "icon": "📚", "name": "Literature & Publishing Hub", "page": "7_📚_Literature_Publishing_Hub.py"},
    {"id": "domain", "icon": "🔬", "name": "Domain Analytics Hub", "page": "8_🔬_Domain_Analytics_Hub.py"},
    {"id": "integrations", "icon": "🔗", "name": "Integrations Hub", "page": "9_🔗_Integrations_Hub.py"},
    {"id": "admin", "icon": "🛡️", "name": "Admin & Security Center", "page": "10_🛡️_Admin_Security_Center.py"},
    {"id": "collaboration", "icon": "🤝", "name": "Collaboration & Portfolio", "page": "11_🤝_Collaboration_Portfolio.py"},
    {"id": "forensics", "icon": "🕵️", "name": "Forensics Intelligence", "page": "12_🕵️_Forensics_Intelligence.py"},
    {"id": "converter", "icon": "🔄", "name": "Universal Converter", "page": "13_🔄_Universal_Converter.py"},
    {"id": "threat", "icon": "🛡️", "name": "Threat & Scanner Suite", "page": "14_🛡️_Threat_Scanner_Suite.py"},
    {"id": "mission", "icon": "🌍", "name": "Global Mission Control", "page": "15_🌍_Global_Mission_Control.py"},
]

PAGE_COUNT = len(CONSOLIDATED_HUBS)

__all__ = ["CONSOLIDATED_HUBS", "PAGE_COUNT"]

