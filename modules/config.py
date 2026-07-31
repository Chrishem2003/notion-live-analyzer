"""
Configuration module — manages secrets, session state, and app-wide constants.
"""
import os
import base64
import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import streamlit as st
import plotly.express as px

from modules.logging_utils import get_logger

logger = get_logger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = APP_DIR / "assets"
CACHE_DIR = APP_DIR / ".cache"

# ─── Defaults ─────────────────────────────────────────────────────────
DEFAULT_REFRESH_OPTIONS = {
    "Off": 0,
    "30 sec": 30,
    "60 sec": 60,
    "5 min": 300,
    "15 min": 900,
}

DEFAULT_KEEP_ALIVE_OPTIONS = {
    "1 min": 60,
    "5 min": 300,
    "10 min": 600,
    "15 min": 900,
}

# ─── Cache ────────────────────────────────────────────────────────────
DEFAULT_CACHE_TTL = 300  # 5 minutes (was 60s)
NOTION_API_CACHE_TTL = 600  # 10 minutes for API calls (database list etc.)
NOTION_DATA_CACHE_TTL = 300  # 5 minutes for Notion data

CHART_COLOR_PALETTES = {
    "Plotly": px.colors.qualitative.Plotly,
    "Set2": px.colors.qualitative.Set2,
    "Pastel": px.colors.qualitative.Pastel,
    "Dark2": px.colors.qualitative.Dark2,
    "Bold": px.colors.qualitative.Bold,
    "Safe": px.colors.qualitative.Safe,
    "Vivid": px.colors.qualitative.Vivid,
    "Alphabet": px.colors.qualitative.Alphabet,
    "Antique": px.colors.qualitative.Antique,
    "Prism": px.colors.qualitative.Prism,
}

# ─── Research-Grade Color Palettes ────────────────────────────────────
RESEARCH_PALETTES = {
    "Nature":      ["#3B4992", "#EE0000", "#008B45", "#631879", "#008280", "#BB0021", "#5F559B", "#A20056"],
    "Science":     ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD", "#8C564B", "#E377C2", "#7F7F7F"],
    "The Lancet":  ["#00468B", "#ED0000", "#42B540", "#0099B4", "#925E9F", "#FDAF91", "#AD002A", "#ADB6B6"],
    "JAMA":        ["#374E55", "#DF8F44", "#00A1D5", "#B24745", "#79AF97", "#6A6599", "#80796B", "#F0B49B"],
    "NEJM":        ["#BC3C29", "#0072B5", "#E18727", "#20854E", "#7876B1", "#6F99AD", "#FFDC91", "#EE4C97"],
    "APA Style":   ["#1B3252", "#9CC3D5", "#E5A135", "#43586E", "#7B9CB4", "#D36E3B", "#2E5A6B", "#BBAAB8"],
    "BMJ":         ["#005AB5", "#DC3220", "#009E73", "#F0E442", "#56B4E9", "#E69F00", "#CC79A7", "#000000"],
    "Cell":        ["#D41F1F", "#377EB8", "#4DAF4A", "#FF7F00", "#984EA3", "#A65628", "#F781BF", "#999999"],
    "Research Std": ["#2C3E50", "#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C", "#E67E22"],
}

RESEARCH_PALETTE_NAMES = list(RESEARCH_PALETTES.keys())

# ─── Publication Theme Config ─────────────────────────────────────────
PUBLICATION_CONFIG = {
    "font_family": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "font_size_axis_title": 14,
    "font_size_axis_ticks": 12,
    "font_size_title": 16,
    "font_size_legend": 12,
    "grid_color": "rgba(128,128,128,0.08)",
    "grid_width": 0.8,
    "axis_line_color": "rgba(128,128,128,0.25)",
    "axis_line_width": 1.2,
    "marker_size": 8,
    "marker_opacity": 0.85,
    "line_width": 2.5,
    "bar_opacity": 0.92,
    "bar_corner_radius": 4,
    "hoverlabel_font_size": 13,
    "margin_t": 40,
    "margin_b": 30,
    "margin_l": 50,
    "margin_r": 20,
}

# ─── Session State Initialization ─────────────────────────────────────
def init_session_state():
    """Initialize all session state keys with defaults."""
    defaults = {
        # Auth
        "user_NOTION_TOKEN": "",
        "user_DATABASE_ID": "",
        "creds_validated": False,
        "creds_failed": False,

        # App
        "refresh_choice": "30 sec",
        "keep_alive_enabled": False,
        "keep_alive_interval_sec": 300,
        "last_sync_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "next_auto_refresh_at": 0.0,
        "theme": "light",
        "accent_color": "#1d4ed8",
        "show_onboarding": True,
        "data_source": "notion",
        "chart_palette": "Plotly",

        # Data
        "uploaded_df": None,
        "merged_df": None,
        "active_df": None,

        # Modules
        "variable_metadata": None,
        "saved_dashboards": {},
        "current_dashboard": None,
        "simulation_metadata": None,
        "gs_credentials": None,
        "statistical_results": [],
        "analysis_log": [],

        # Research Project
        "current_project": None,
        "saved_projects": {},
        "findings_repository": [],

        # Hypothesis Generator
        "generated_hypotheses": [],
        "hypothesis_history": [],

        # Sensitivity
        "sensitivity_results": None,

        # NL Query
        "nl_query_history": [],

        # Feature Engineering
        "engineered_features": None,
        "feature_history": [],

        # Meta-Analysis
        "meta_analysis_results": None,

        # Network Analysis
        "network_results": None,
        "network_graph": None,

        # Quality Check
        "quality_report": None,

        # ─── Notion Bi-Directional Sync ────────────────────────────
        "notion_sync_queue": [],
        "notion_sync_history": [],
        "notion_page_ids": {},

        # ─── Executive Storyteller ─────────────────────────────────
        "executive_report": None,
        "executive_report_generated": False,

        # ─── Git Integration ───────────────────────────────────────
        "git_connected": False,
        "git_repo_url": "",
        "git_token": "",
        "git_branch": "main",
        "git_last_sync": None,
        "git_commit_history": [],

        # ─── Presentation Deck Builder ─────────────────────────────
        "deck_slides": [],
        "deck_charts": [],
        "deck_current_slide": 0,
        "deck_title": "Untitled Presentation",

        # ─── Notion Embed UI ───────────────────────────────────────
        "compact_mode": False,
        "notion_embed_mode": False,

        # ─── Literature Aggregator Engine ──────────────────────────
        "lit_engine_project_id": None,
        "lit_engine_last_topic": "",
        "lit_engine_last_country": "",
        "lit_engine_fetch_count": 0,
        "lit_engine_generated_report": None,

        # ─── Audit & Compliance Hub ──────────────────────────────
        "forensic_unlocked": False,
        "_last_audit_results": None,
        "_last_audit_text": "",
        "_last_audit_source": "",
        "_last_optimized_text": "",
        "_last_optimized_stats": None,
        "_export_report": "",

        # ─── Application Pipeline & Document Vault ──────────────
        "pipeline_manager": None,
        "pipeline_selected_app": None,
        "pipeline_active_tab": "kanban",
        "pipeline_applications": [],
        "pipeline_documents": [],
        "pipeline_currencies": {},

        # ─── Global Localization Engine ─────────────────────────
        "loc_selected_language": "en",
        "loc_selected_accent": "Academic US",
        "loc_selected_glossary": "bio",
        "loc_academic_tone": "peer_reviewed",
        "loc_preserve_tech_terms": True,
        "loc_dual_view_enabled": True,
        "loc_offline_pack_enabled": True,
        "loc_institutional_policy": True,
        "loc_region_filter": "All Regions",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

# ─── Secret Resolution ────────────────────────────────────────────────
def get_secret(name: str) -> Optional[str]:
    """Resolve a secret value — session override > st.secrets > env var."""
    session_key = f"user_{name}"
    if session_key in st.session_state and st.session_state[session_key]:
        return st.session_state[session_key]
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        # No secrets.toml (or it is unreadable) — fall back to the environment.
        logger.debug("Could not read secret %r from st.secrets", name, exc_info=True)
    return os.environ.get(name)

# ─── Background Image ─────────────────────────────────────────────────
def find_background_image() -> Optional[Path]:
    """Search for a background image in the assets directory."""
    candidates = [
        ASSETS_DIR / "background.png",
        ASSETS_DIR / "background.jpg",
        ASSETS_DIR / "background.jpeg",
        ASSETS_DIR / "background.webp",
        ASSETS_DIR / "background.gif",
        APP_DIR / "images" / "background.png",
        APP_DIR / "images" / "background.jpg",
        APP_DIR / "images" / "background.jpeg",
        APP_DIR / "images" / "background.webp",
        APP_DIR / "images" / "background.gif",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None

def image_to_data_url(path: Path) -> str:
    """Convert an image file to a base64 data URL."""
    ext = path.suffix.lower().lstrip(".")
    mime_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
        "svg": "image/svg+xml",
    }
    mime = mime_map.get(ext, "application/octet-stream")
    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

# ─── Cache Persistence ────────────────────────────────────────────────
def save_cache(key: str, data: Any):
    """Save data to disk cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{key}.pkl"
    with open(cache_file, "wb") as f:
        pickle.dump(data, f)

def load_cache(key: str) -> Optional[Any]:
    """Load data from disk cache."""
    cache_file = CACHE_DIR / f"{key}.pkl"
    if cache_file.exists():
        with open(cache_file, "rb") as f:
            return pickle.load(f)
    return None

def clear_cache():
    """Clear all cached data."""
    if CACHE_DIR.exists():
        import shutil
        shutil.rmtree(CACHE_DIR)
        CACHE_DIR.mkdir(parents=True)
