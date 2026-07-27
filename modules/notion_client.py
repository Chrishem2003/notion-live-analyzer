"""
Notion API Client — handles all interactions with the Notion API.
Supports all 20+ property types and automatic database detection.
Includes caching and rate-limiting to improve performance.
"""
import hashlib
import time
import functools
from typing import Optional, List, Dict, Any, Tuple, Callable
from datetime import datetime, timedelta
import requests
import pandas as pd
import streamlit as st

from modules.pandas_compat import is_text_dtype
from modules.logging_utils import get_logger

logger = get_logger(__name__)

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
PAGE_SIZE = 100

# ─── Simple In-Memory Cache ──────────────────────────────────────────
# Avoids duplicate API calls within the same request cycle
_request_cache: Dict[str, tuple] = {}
_request_cache_ttl: int = 60  # seconds

def _cached_request(cache_key: str, ttl: int = 60):
    """Decorator to cache API responses in-memory for the request cycle."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Skip cache if explicitly requested with force_refresh=True
            if kwargs.pop("force_refresh", False):
                return func(*args, **kwargs)
            
            full_key = f"{cache_key}:{hash(str(args) + str(kwargs))}"
            now = time.time()
            
            if full_key in _request_cache:
                cached_at, cached_value = _request_cache[full_key]
                if now - cached_at < ttl:
                    return cached_value
            
            result = func(*args, **kwargs)
            # Empty results usually mean the call failed; caching them would
            # hide the failure for the whole TTL.
            if result:
                _request_cache[full_key] = (now, result)
            return result
        return wrapper
    return decorator

def clear_request_cache():
    """Clear the in-memory request cache."""
    _request_cache.clear()

# ─── Rate Limiter ────────────────────────────────────────────────────
# Notion API allows 3 requests per second; we pace ourselves.
class RateLimiter:
    def __init__(self, max_calls: int = 3, per_seconds: float = 1.0):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self.calls: List[float] = []
    
    def wait_if_needed(self):
        """Wait if we've exceeded the rate limit."""
        now = time.time()
        # Remove calls older than the window
        self.calls = [t for t in self.calls if now - t < self.per_seconds]
        
        if len(self.calls) >= self.max_calls:
            sleep_time = self.calls[0] + self.per_seconds - now
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        self.calls.append(time.time())

_rate_limiter = RateLimiter(max_calls=3, per_seconds=1.0)

def _rate_limited_request(method: str, url: str, **kwargs) -> requests.Response:
    """Make a rate-limited HTTP request to the Notion API."""
    _rate_limiter.wait_if_needed()
    
    # Add timeout default
    kwargs.setdefault("timeout", 30)
    
    return requests.request(method, url, **kwargs)

# ─── Universal Property Parser ────────────────────────────────────────
def extract_rich_text(rich_text_list: list) -> str:
    """Extract plain text from a Notion rich text array."""
    if not rich_text_list:
        return ""
    return "".join(
        item.get("plain_text", "") for item in rich_text_list if isinstance(item, dict)
    )

def parse_formula(formula_obj: dict) -> Any:
    """Parse a Notion formula property."""
    if not formula_obj:
        return None
    formula_type = formula_obj.get("type")
    if formula_type:
        return formula_obj.get(formula_type)
    return None

def parse_rollup(rollup_obj: dict) -> Any:
    """Parse a Notion rollup property."""
    if not rollup_obj:
        return None
    rollup_type = rollup_obj.get("type")
    if rollup_type == "array":
        return rollup_obj.get("array", [])
    return rollup_obj.get(rollup_type) if rollup_type else None

NOTION_PROPERTY_PARSERS = {
    "title": lambda p: extract_rich_text(p.get("title", [])),
    "rich_text": lambda p: extract_rich_text(p.get("rich_text", [])),
    "number": lambda p: p.get("number"),
    "select": lambda p: p.get("select", {}).get("name") if p.get("select") else None,
    "multi_select": lambda p: [s["name"] for s in p.get("multi_select", [])] if p.get("multi_select") else [],
    "status": lambda p: p.get("status", {}).get("name") if p.get("status") else None,
    "date": lambda p: p.get("date", {}).get("start") if p.get("date") else None,
    "checkbox": lambda p: p.get("checkbox", False),
    "email": lambda p: p.get("email"),
    "phone": lambda p: p.get("phone"),
    "url": lambda p: p.get("url"),
    "formula": lambda p: parse_formula(p.get("formula", {})),
    "relation": lambda p: [r["id"] for r in p.get("relation", [])] if p.get("relation") else [],
    "rollup": lambda p: parse_rollup(p.get("rollup", {})),
    "people": lambda p: [
        person.get("name", person.get("id", ""))
        for person in p.get("people", [])
        if isinstance(person, dict)
    ] if p.get("people") else [],
    "files": lambda p: [
        f.get("name", f.get("external", {}).get("url", ""))
        for f in p.get("files", [])
    ] if p.get("files") else [],
    "created_by": lambda p: p.get("created_by", {}).get("name", "Unknown"),
    "created_time": lambda p: p.get("created_time"),
    "last_edited_by": lambda p: p.get("last_edited_by", {}).get("name", "Unknown"),
    "last_edited_time": lambda p: p.get("last_edited_time"),
    "unique_id": lambda p: (
        f"{p.get('unique_id', {}).get('prefix', '')}-{p.get('unique_id', {}).get('number', '')}"
        if p.get("unique_id")
        else None
    ),
    "button": lambda p: p.get("button", {}).get("action", ""),
}

# ─── API Utilities ────────────────────────────────────────────────────
def _make_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

def _handle_api_error(response: requests.Response, token: str, db_id: str = None):
    """Handle common Notion API errors and trigger credential reset if needed."""
    if response.status_code in (401, 403):
        st.session_state["creds_failed"] = True
        st.error("🔐 Your Notion token is invalid or lacks access. Please re-enter your credentials below.")
        return True
    if response.status_code == 429:
        st.warning("⏳ Rate limited by Notion API. Waiting 1 second...")
        time.sleep(1)
        return False
    if response.status_code == 404 and db_id:
        st.warning(f"Database {db_id} not found. It may have been deleted or the ID is incorrect.")
        return True
    # Error boundary: catch 400 validation errors (e.g., Page ID passed instead of Database ID)
    if response.status_code == 400:
        st.warning("⚠️ Invalid database ID. You may have passed a Page ID instead of a Database ID.")
        return pd.DataFrame()
    return False

# ─── Database Operations ──────────────────────────────────────────────
@_cached_request("get_database_options", ttl=300)  # Cache for 5 minutes
def get_database_options(token: str) -> List[Dict]:
    """Search and list all accessible databases (cached for 5 min)."""
    url = f"{NOTION_API_URL}/search"
    headers = _make_headers(token)
    payload = {
        "query": "",
        "filter": {"property": "object", "value": "database"},
        "page_size": 100,
    }
    databases = []
    try:
        has_more = True
        next_cursor = None
        max_pages = 3  # Limit pagination to avoid timeout
        page_count = 0
        while has_more and page_count < max_pages:
            request_payload = payload.copy()
            if next_cursor:
                request_payload["start_cursor"] = next_cursor
            response = _rate_limited_request("POST", url, json=request_payload, headers=headers)
            if response.status_code != 200:
                logger.error(
                    "Notion database search failed (page %s): %s — %s",
                    page_count + 1, response.status_code, response.text[:200],
                )
                if not _handle_api_error(response, token):
                    st.error(
                        f"Could not list Notion databases (HTTP {response.status_code}). "
                        "Showing any databases retrieved so far."
                    )
                break
            data = response.json()
            for db in data.get("results", []):
                title = extract_rich_text(db.get("title", [])) or db["id"]
                databases.append({
                    "id": db["id"],
                    "title": title,
                    "properties": db.get("properties", {}),
                    "created_time": db.get("created_time", ""),
                })
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")
            page_count += 1
    except Exception as e:
        logger.exception("Error fetching Notion databases")
        st.error(f"Error fetching databases: {str(e)}")
    return databases

def fingerprint_database(properties: dict) -> str:
    """Create a unique SHA-256 fingerprint from property names + types."""
    schema_items = []
    for name, prop in sorted(properties.items()):
        if isinstance(prop, dict):
            prop_type = prop.get("type", "unknown")
            schema_items.append(f"{name}:{prop_type}")
    fingerprint_str = "|".join(schema_items)
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()

def auto_find_duplicated_db(token: str, original_fingerprint: str) -> Optional[str]:
    """
    Search all databases for one matching the original fingerprint.
    Used when users duplicate the workspace to their own Notion.
    """
    databases = get_database_options(token)
    for db in databases:
        fp = fingerprint_database(db.get("properties", {}))
        if fp == original_fingerprint:
            return db["id"]
    # Second pass: try with property names only (more lenient)
    for db in databases:
        props = db.get("properties", {})
        prop_types = sorted([f"{p.get('type', '')}" for p in props.values() if isinstance(p, dict)])
        if prop_types:
            fp = hashlib.sha256("|".join(prop_types).encode()).hexdigest()
            if fp[:16] == original_fingerprint[:16]:
                return db["id"]
    return None

def discover_database_id(token: str) -> Optional[str]:
    """Auto-discover the best database to use based on schema richness."""
    databases = get_database_options(token)
    best_match = None
    best_score = -1
    for db in databases:
        props = db.get("properties", {})
        property_types = {p.get("type") for p in props.values() if isinstance(p, dict)}
        score = 0
        if "title" in property_types:
            score += 5
        if "number" in property_types:
            score += 5
        if "date" in property_types:
            score += 4
        if {"select", "status"}.intersection(property_types):
            score += 5
        if "multi_select" in property_types:
            score += 3
        score += len(property_types)  # More diverse types = richer schema
        if score > best_score:
            best_score = score
            best_match = db["id"]
    return best_match

# ─── Data Fetching ────────────────────────────────────────────────────
def fetch_notion_data(token: str, db_id: str) -> pd.DataFrame:
    """
    Fetch all pages from a Notion database and return a DataFrame.
    Parses ALL property types automatically.
    Uses rate-limited requests to avoid 429 errors.
    
    Error Boundary: Returns empty DataFrame gracefully if HTTP 400 (Page ID passed instead of Database ID).
    """
    if not db_id or not db_id.strip():
        st.warning("No Database ID provided.")
        return pd.DataFrame()
    
    url = f"{NOTION_API_URL}/databases/{db_id}/query"
    headers = _make_headers(token)
    rows = []
    has_more = True
    next_cursor = None

    # First, get the database schema (cached per request)
    schema_url = f"{NOTION_API_URL}/databases/{db_id}"
    try:
        schema_response = _rate_limited_request("GET", schema_url, headers=headers)
        property_definitions = {}
        if schema_response.status_code == 200:
            schema_data = schema_response.json()
            property_definitions = schema_data.get("properties", {})
        else:
            if _handle_api_error(schema_response, token, db_id):
                return pd.DataFrame()
    except Exception as e:
        logger.exception("Error fetching schema for Notion database %s", db_id)
        st.error(f"Error fetching database schema: {str(e)}")
        return pd.DataFrame()

    fetch_attempts = 0
    max_attempts = 2  # Reduced from 3

    while has_more and fetch_attempts < max_attempts:
        payload = {"page_size": min(PAGE_SIZE, 50)}  # Reduced page size for faster first load
        if next_cursor:
            payload["start_cursor"] = next_cursor

        try:
            response = _rate_limited_request("POST", url, json=payload, headers=headers)
            if _handle_api_error(response, token, db_id):
                return pd.DataFrame()

            if response.status_code != 200:
                logger.error(
                    "Notion query failed for database %s: %s — %s",
                    db_id, response.status_code, response.text[:200],
                )
                st.error(f"Notion API Error: {response.status_code} — {response.text[:200]}")
                fetch_attempts += 1
                continue

            data = response.json()
            for page in data.get("results", []):
                props = page.get("properties", {})
                row = {}
                for prop_name, prop_def in property_definitions.items():
                    prop_type = prop_def.get("type", "unknown")
                    prop_value = props.get(prop_name, {})
                    parser = NOTION_PROPERTY_PARSERS.get(prop_type, lambda p: str(p))
                    try:
                        parsed = parser(prop_value)
                        # Flatten lists for CSV-friendly output
                        if isinstance(parsed, list):
                            parsed = ", ".join(str(item) for item in parsed) if parsed else None
                        row[prop_name] = parsed
                    except Exception:
                        logger.warning(
                            "Failed to parse Notion property %r (type %s) on page %s",
                            prop_name, prop_type, page.get("id", "?"), exc_info=True,
                        )
                        row[prop_name] = None

                # Also add metadata
                row["_page_id"] = page.get("id", "")
                row["_created_time"] = page.get("created_time", "")
                row["_last_edited_time"] = page.get("last_edited_time", "")
                rows.append(row)

            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")
            fetch_attempts = 0  # Reset on success

        except requests.exceptions.Timeout:
            logger.warning("Timeout querying Notion database %s — retrying", db_id)
            st.warning("⏱️ Notion API timeout. Retrying...")
            fetch_attempts += 1
            time.sleep(1)
        except Exception as e:
            logger.exception("Error fetching rows from Notion database %s", db_id)
            st.error(f"Error fetching data: {str(e)}")
            fetch_attempts += 1
            time.sleep(0.5)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Auto-type inference (optimized)
    for col in df.columns:
        if col.startswith("_"):
            continue
        if is_text_dtype(df[col]):
            try:
                numeric_series = pd.to_numeric(df[col], errors="coerce")
                if numeric_series.notna().sum() > len(df) * 0.5:
                    df[col] = numeric_series
            except (ValueError, TypeError):
                logger.debug("Numeric type inference skipped for column %r", col, exc_info=True)

    return df

@_cached_request("get_database_schema", ttl=600)  # Cache for 10 minutes
def get_database_schema(token: str, db_id: str) -> Dict:
    """Get the schema/property definitions of a Notion database (cached for 10 min)."""
    url = f"{NOTION_API_URL}/databases/{db_id}"
    headers = _make_headers(token)
    try:
        response = _rate_limited_request("GET", url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("properties", {})
        logger.error(
            "Failed to fetch schema for Notion database %s: %s — %s",
            db_id, response.status_code, response.text[:200],
        )
        return {}
    except Exception:
        logger.exception("Error fetching schema for Notion database %s", db_id)
        return {}

