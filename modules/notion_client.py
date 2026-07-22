"""
Notion API Client — handles all interactions with the Notion API.
Supports all 20+ property types and automatic database detection.
"""
import hashlib
import time
from typing import Optional, List, Dict, Any, Tuple
import requests
import pandas as pd
import streamlit as st

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
PAGE_SIZE = 100

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
    return False

# ─── Database Operations ──────────────────────────────────────────────
def get_database_options(token: str) -> List[Dict]:
    """Search and list all accessible databases."""
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
        while has_more:
            request_payload = payload.copy()
            if next_cursor:
                request_payload["start_cursor"] = next_cursor
            response = requests.post(url, json=request_payload, headers=headers, timeout=30)
            if response.status_code != 200:
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
    except Exception as e:
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
    """
    url = f"{NOTION_API_URL}/databases/{db_id}/query"
    headers = _make_headers(token)
    rows = []
    has_more = True
    next_cursor = None

    # First, get the database schema
    schema_url = f"{NOTION_API_URL}/databases/{db_id}"
    schema_response = requests.get(schema_url, headers=headers, timeout=30)
    property_definitions = {}
    if schema_response.status_code == 200:
        schema_data = schema_response.json()
        property_definitions = schema_data.get("properties", {})
    else:
        if _handle_api_error(schema_response, token, db_id):
            return pd.DataFrame()

    fetch_attempts = 0
    max_attempts = 3

    while has_more and fetch_attempts < max_attempts:
        payload = {"page_size": PAGE_SIZE}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if _handle_api_error(response, token, db_id):
                return pd.DataFrame()

            if response.status_code != 200:
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
            st.warning("⏱️ Notion API timeout. Retrying...")
            fetch_attempts += 1
            time.sleep(2)
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
            fetch_attempts += 1
            time.sleep(1)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Auto-type inference
    for col in df.columns:
        if col.startswith("_"):
            continue
        # Try numeric conversion
        if df[col].dtype == object:
            try:
                numeric_series = pd.to_numeric(df[col], errors="coerce")
                if numeric_series.notna().sum() > len(df) * 0.5:
                    df[col] = numeric_series
            except (ValueError, TypeError):
                pass

    return df

def get_database_schema(token: str, db_id: str) -> Dict:
    """Get the schema/property definitions of a Notion database."""
    url = f"{NOTION_API_URL}/databases/{db_id}"
    headers = _make_headers(token)
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("properties", {})
        return {}
    except Exception:
        return {}

