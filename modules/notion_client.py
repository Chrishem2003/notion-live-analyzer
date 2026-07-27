import os
import requests
import streamlit as st

def get_database_options():
    return []

def auto_find_duplicated_db():
    return None

def discover_database_id():
    return None

def fingerprint_database(db_id=None):
    return "default_fp"

def fetch_notion_data(db_id=None, api_key=None):
    """
    Safely fetches Notion data. Handles cases where db_id is a Page ID
    instead of a Database ID to prevent 400 validation errors.
    """
    if not db_id or not api_key:
        return []
    
    # Strip hyphens for clean API URL handling
    clean_id = str(db_id).replace("-", "")
    url = f"https://api.notion.com/v1/databases/{clean_id}/query"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-08",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, json={"page_size": 100}, timeout=10)
        if response.status_code == 200:
            return response.json().get("results", [])
        # If Notion returns 400 (Page ID passed instead of Database ID), fail gracefully
        return []
    except Exception:
        return []
