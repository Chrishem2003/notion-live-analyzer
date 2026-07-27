import os
import requests
import pandas as pd
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
    Safely fetches Notion data. Returns a pandas DataFrame to prevent
    AttributeErrors when checking 'df.empty'.
    """
    if not db_id or not api_key:
        return pd.DataFrame()
    
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
            results = response.json().get("results", [])
            return pd.DataFrame(results) if results else pd.DataFrame()
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()
