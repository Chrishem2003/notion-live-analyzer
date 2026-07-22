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
        pass
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



