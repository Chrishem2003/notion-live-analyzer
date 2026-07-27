"""Auth — Security & Secrets Management."""
import os
import streamlit as st

def get_notion_token() -> str:
    """Extract Notion token from st.secrets with fallback to env vars."""
    # Session override takes priority
    if st.session_state.get("user_NOTION_TOKEN"):
        return st.session_state["user_NOTION_TOKEN"]
    # Try st.secrets
    try:
        if hasattr(st, 'secrets'):
            for key in ("NOTION_TOKEN", "NOTION_API_KEY", "notion_token"):
                if key in st.secrets:
                    return str(st.secrets[key])
    except Exception:
        pass
    # Fall back to env var
    return os.environ.get("NOTION_TOKEN", "") or os.environ.get("NOTION_API_KEY", "")

def get_database_id() -> str:
    """Extract Database ID from st.secrets with fallback to env vars."""
    if st.session_state.get("user_DATABASE_ID"):
        return st.session_state["user_DATABASE_ID"]
    try:
        if hasattr(st, 'secrets'):
            for key in ("NOTION_DATABASE_ID", "DATABASE_ID", "notion_database_id"):
                if key in st.secrets:
                    return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get("NOTION_DATABASE_ID", "") or os.environ.get("DATABASE_ID", "")

def has_credentials() -> bool:
    """Check if credentials are present."""
    return bool(get_notion_token())

def check_authentication() -> bool:
    """Validate credentials are present. Returns True if valid."""
    return has_credentials()

def validate_credentials(token: str, db_id: str = None) -> bool:
    """Validate token format (basic check)."""
    if not token:
        return False
    if not token.startswith("ntn_"):
        return False
    return True

def save_credentials(token: str, db_id: str = ""):
    """Save credentials to session state."""
    st.session_state["user_NOTION_TOKEN"] = token
    st.session_state["user_DATABASE_ID"] = db_id
    st.session_state["creds_validated"] = True

def clear_credentials():
    """Clear stored credentials."""
    st.session_state["user_NOTION_TOKEN"] = ""
    st.session_state["user_DATABASE_ID"] = ""
    st.session_state["creds_validated"] = False
    st.session_state["creds_failed"] = False