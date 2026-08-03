import security_guard

from notion_client import Client
import streamlit as st

def auto_detect_database_ids(notion_token: str, required_titles: list) -> dict:
    """
    Scans the user's connected Notion workspace and returns a dictionary 
    mapping database titles to their actual Notion Database IDs.
    """
    notion = Client(auth=notion_token)
    detected_databases = {}
    
    try:
        response = notion.search(
            query="",
            filter={"value": "database", "property": "object"},
            page_size=100
        )
        
        for result in response.get("results", []):
            title_objects = result.get("title", [])
            if title_objects:
                db_title = "".join([t.get("plain_text", "") for t in title_objects]).strip()
                db_id = result.get("id")
                
                if db_title in required_titles:
                    detected_databases[db_title] = db_id
                    
    except Exception as e:
        st.error(f"Error scanning Notion workspace: {e}")
        
    return detected_databases
