
"""
Notion Bi-Directional Sync Engine  enables writing insights, tags, and cleaned data
back to Notion pages and databases via the Notion API.
"""
from typing import Dict, List, Any, Optional, Tuple
import time
from datetime import datetime
import requests
import pandas as pd
import streamlit as st

from modules.config import get_secret
from modules.logging_utils import get_logger

logger = get_logger(__name__)

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionSyncEngine:
    """Handles bi-directional sync between Streamlit app and Notion databases."""

    def __init__(self, token: str = None):
        self.token = token or get_secret("NOTION_TOKEN")
        if not self.token:
            raise ValueError("Notion API token is required for sync operations")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    # â”€â”€â”€ Page Property Update â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def update_page_property(
        self, page_id: str, property_name: str, property_value: Any, property_type: str = "rich_text"
    ) -> Tuple[bool, str]:
        """
        Update a single property on a Notion page.
        Supports: rich_text, title, number, select, status, checkbox, date, email, phone, url.
        """
        url = f"{NOTION_API_URL}/pages/{page_id}"
        headers = self._headers()

        payload = self._build_property_payload(property_name, property_value, property_type)
        if "error" in payload:
            return False, payload["error"]

        try:
            response = requests.patch(url, json={"properties": payload}, headers=headers, timeout=15)
            if response.status_code == 200:
                return True, f"✅ Updated '{property_name}' on page {page_id[:8]}..."
            elif response.status_code == 401:
                return False, "âŒ Invalid token  please re-connect your Notion integration"
            elif response.status_code == 404:
                return False, f"âŒ Page {page_id[:8]}... not found  it may have been deleted"
            else:
                return False, f"âŒ API Error {response.status_code}: {response.text[:200]}"
        except requests.exceptions.Timeout:
            logger.warning("Timeout updating property %r on Notion page %s", property_name, page_id)
            return False, "â±ï¸ Request timed out  check your network"
        except Exception as e:
            logger.exception("Failed to update property %r on Notion page %s", property_name, page_id)
            return False, f"âŒ Sync error: {str(e)}"

    def _build_property_payload(self, name: str, value: Any, ptype: str) -> Dict:
        """Build the Notion API property payload based on type."""
        if value is None:
            return {name: None}

        if ptype == "rich_text":
            return {name: {"rich_text": [{"text": {"content": str(value)}}]}}
        elif ptype == "title":
            return {name: {"title": [{"text": {"content": str(value)}}]}}
        elif ptype == "number":
            try:
                return {name: {"number": float(value)}}
            except (ValueError, TypeError):
                return {"error": f"Cannot convert '{value}' to number"}
        elif ptype == "select":
            return {name: {"select": {"name": str(value)}}}
        elif ptype == "status":
            return {name: {"status": {"name": str(value)}}}
        elif ptype == "checkbox":
            return {name: {"checkbox": bool(value)}}
        elif ptype == "date":
            return {name: {"date": {"start": str(value)}}}
        elif ptype == "email":
            return {name: {"email": str(value)}}
        elif ptype == "phone":
            return {name: {"phone_number": str(value)}}
        elif ptype == "url":
            return {name: {"url": str(value)}}
        elif ptype == "multi_select":
            if isinstance(value, list):
                return {name: {"multi_select": [{"name": v} for v in value]}}
            return {name: {"multi_select": [{"name": str(value)}]}}
        else:
            # Default to rich_text
            return {name: {"rich_text": [{"text": {"content": str(value)}}]}}

    # â”€â”€â”€ Add Comment to Page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def add_page_comment(self, page_id: str, comment_text: str) -> Tuple[bool, str]:
        """Add a discussion comment to a Notion page (AI insight, note, etc.)."""
        url = f"{NOTION_API_URL}/comments"
        headers = self._headers()

        payload = {
            "parent": {"page_id": page_id},
            "rich_text": [{"text": {"content": comment_text}}],
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                return True, "✅ Comment added to page"
            else:
                logger.error(
                    "Failed to add comment to Notion page %s: %s  %s",
                    page_id, response.status_code, response.text[:200],
                )
                return False, f"âŒ Failed to add comment: {response.status_code}"
        except Exception as e:
            logger.exception("Error adding comment to Notion page %s", page_id)
            return False, f"âŒ Comment error: {str(e)}"

    # â”€â”€â”€ Create Database Entry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def create_database_entry(
        self, db_id: str, properties: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new entry (page) in a Notion database.
        Returns (success, message, new_page_id).
        """
        url = f"{NOTION_API_URL}/pages"
        headers = self._headers()

        # Build property payload
        notion_properties = {}
        rejected: List[str] = []
        for prop_name, prop_info in properties.items():
            if isinstance(prop_info, dict):
                ptype = prop_info.get("type", "rich_text")
                pvalue = prop_info.get("value")
            else:
                ptype = "rich_text"
                pvalue = prop_info

            payload = self._build_property_payload(prop_name, pvalue, ptype)
            if "error" in payload:
                logger.warning("Skipping property %r: %s", prop_name, payload["error"])
                rejected.append(f"{prop_name} ({payload['error']})")
                continue
            notion_properties.update(payload)

        if not notion_properties:
            return False, f"âŒ No valid properties to write  {'; '.join(rejected)}", None

        payload = {
            "parent": {"database_id": db_id},
            "properties": notion_properties,
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                new_id = data.get("id", "")
                message = "✅ New entry created in Notion database"
                if rejected:
                    message = f"  skipped invalid properties: {'; '.join(rejected)}"
                return True, message, new_id
            else:
                logger.error(
                    "Failed to create entry in Notion database %s: %s  %s",
                    db_id, response.status_code, response.text[:200],
                )
                return False, f"âŒ Failed to create entry: {response.status_code}  {response.text[:200]}", None
        except Exception as e:
            logger.exception("Error creating entry in Notion database %s", db_id)
            return False, f"âŒ Create error: {str(e)}", None

    # â”€â”€â”€ Batch Sync Insights â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def batch_sync_insights(
        self, df: pd.DataFrame, insights: List[Dict[str, Any]], target_property: str = "AI_Insight"
    ) -> Dict[str, Any]:
        """
        Batch-sync AI-generated insights back to their source Notion pages.
        Expects df to have '_page_id' column mapping to Notion page IDs.
        """
        if "_page_id" not in df.columns:
            return {
                "success": False,
                "message": "No '_page_id' column found. Data must be sourced from Notion for bi-directional sync.",
                "synced": 0,
                "failed": 0,
            }

        synced = 0
        failed = 0
        errors = []

        for idx, row in df.iterrows():
            page_id = row.get("_page_id")
            if not page_id or page_id == "unknown":
                failed = 1
                continue

            # Find matching insight
            matching_insight = None
            for insight in insights:
                if insight.get("page_id") == page_id or insight.get("row_index") == idx:
                    matching_insight = insight
                    break

            if matching_insight:
                insight_text = matching_insight.get("insight", matching_insight.get("text", ""))
                success, msg = self.update_page_property(
                    page_id, target_property, insight_text, "rich_text"
                )
                if success:
                    synced = 1
                else:
                    failed = 1
                    errors.append(msg)

                # Also add as a comment
                comment_ok, comment_msg = self.add_page_comment(
                    page_id, f"ðŸ¤– AI Insight: {insight_text[:200]}"
                )
                if not comment_ok:
                    errors.append(f"{page_id[:8]}: {comment_msg}")

                time.sleep(0.35)  # Rate limiting

        return {
            "success": synced > 0,
            "message": f"Synced {synced} insights, {failed} failed",
            "synced": synced,
            "failed": failed,
            "errors": errors[:5],
        }

    # â”€â”€â”€ Sync Cleaned Data Column â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def sync_cleaned_column(
        self, df: pd.DataFrame, column_name: str, target_property: str = None
    ) -> Dict[str, Any]:
        """
        Write a cleaned/transformed column back to Notion.
        """
        if "_page_id" not in df.columns:
            return {"success": False, "message": "No _page_id column for round-trip sync", "synced": 0, "failed": 0}

        target = target_property or column_name
        synced = 0
        failed = 0

        for idx, row in df.iterrows():
            page_id = row.get("_page_id")
            if not page_id:
                failed = 1
                continue

            value = row.get(column_name)
            # Infer type
            if isinstance(value, bool):
                ptype = "checkbox"
            elif isinstance(value, (int, float)):
                ptype = "number"
            elif pd.isna(value):
                ptype = "rich_text"
                value = ""
            else:
                ptype = "rich_text"

            success, msg = self.update_page_property(page_id, target, value, ptype)
            if success:
                synced = 1
            else:
                failed = 1
            time.sleep(0.35)

        return {
            "success": synced > 0,
            "message": f"Synced '{column_name}' to '{target}'  {synced} updated, {failed} failed",
            "synced": synced,
            "failed": failed,
        }

    # â”€â”€â”€ Get Page Content â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def get_page_content(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full page content including block children."""
        url = f"{NOTION_API_URL}/blocks/{page_id}/children"
        headers = self._headers()

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.json()
            logger.error(
                "Failed to read content of Notion page %s: %s  %s",
                page_id, response.status_code, response.text[:200],
            )
            return None
        except Exception:
            logger.exception("Error reading content of Notion page %s", page_id)
            return None

    # â”€â”€â”€ Append Block to Page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def append_block(self, page_id: str, block_type: str, content: Dict) -> Tuple[bool, str]:
        """Append a content block to a Notion page (e.g., callout, paragraph, heading)."""
        url = f"{NOTION_API_URL}/blocks/{page_id}/children"
        headers = self._headers()

        block = {
            "object": "block",
            "type": block_type,
            block_type: content,
        }

        try:
            response = requests.patch(url, json={"children": [block]}, headers=headers, timeout=15)
            if response.status_code == 200:
                return True, f"✅ Block appended to page {page_id[:8]}..."
            logger.error(
                "Failed to append %s block to Notion page %s: %s  %s",
                block_type, page_id, response.status_code, response.text[:200],
            )
            return False, f"âŒ Failed: {response.status_code}"
        except Exception as e:
            logger.exception("Error appending %s block to Notion page %s", block_type, page_id)
            return False, f"âŒ Error: {str(e)}"


# â”€â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def render_notion_sync_ui(df: pd.DataFrame):
    """Render the Notion sync UI  embeddable in other pages."""
    st.markdown("### ðŸ”„ Notion Bi-Directional Sync")
    st.caption("Push insights, tags, and cleaned data back to your Notion database.")

    has_page_ids = "_page_id" in df.columns if df is not None else False

    if not has_page_ids:
        st.info(
            "ðŸ’¡ **Bi-directional sync requires data sourced from Notion.** "
            "The `_page_id` column is missing  load data from a Notion database first."
        )
        return

    sync_engine = NotionSyncEngine()

    tab1, tab2, tab3 = st.tabs(["ðŸ“¤ Push Insights", "ðŸ“ Push Cleaned Data", "📋 Sync History"])

    with tab1:
        st.subheader("ðŸ“¤ Push AI Insights to Notion")
        st.caption("Select insights to write back to their source Notion pages.")

        insights = st.session_state.get("generated_hypotheses", [])
        if insights:
            st.info(f" {len(insights)} insights available for sync")
            insight_text = st.text_area(
                "Insight to sync (edit as needed)",
                value=insights[0].get("narrative", str(insights[0])) if insights else "",
                height=100,
            )
            target_prop = st.text_input("Notion property name to update", value="AI_Insight")

            if st.button("ðŸš€ Push Insight to Notion Pages", type="primary"):
                with st.spinner("Syncing insights to Notion..."):
                    result = sync_engine.batch_sync_insights(
                        df, [{"row_index": 0, "insight": insight_text}], target_prop
                    )
                if result["success"]:
                    st.success(result["message"])
                else:
                    st.warning(result["message"])
                    for err in result.get("errors", []):
                        st.error(err)

                # Add to history
                st.session_state["notion_sync_history"].append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "insight_push",
                    "result": result,
                })
        else:
            st.info("No insights generated yet. Run hypothesis discovery first.")

    with tab2:
        st.subheader("ðŸ“ Push Cleaned/Transformed Data")
        st.caption("Write transformed columns back to Notion.")

        cols_without_meta = [c for c in df.columns if not c.startswith("_")]
        column_to_sync = st.selectbox("Select column to sync back", options=cols_without_meta)
        target_property = st.text_input("Target Notion property name", value=column_to_sync)

        if st.button("ðŸ”„ Sync Column to Notion", type="primary"):
            with st.spinner(f"Syncing '{column_to_sync}' to Notion..."):
                result = sync_engine.sync_cleaned_column(df, column_to_sync, target_property)
            if result["success"]:
                st.success(result["message"])
            else:
                st.warning(result["message"])

            st.session_state["notion_sync_history"].append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "column_sync",
                "column": column_to_sync,
                "result": result,
            })

        # Quick actions
        st.markdown("#### âš¡ Quick Actions")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Sync 'Significant' Flag", use_container_width=True):
                if "significant" in df.columns:
                    result = sync_engine.sync_cleaned_column(df, "significant", "Significant")
                    st.success(result["message"])
                else:
                    st.warning("No 'significant' column found")
        with col2:
            if st.button("ðŸ·ï¸ Sync Tags/Notes", use_container_width=True):
                for col in ["Tags", "Notes", "Status", "Category"]:
                    if col in df.columns:
                        result = sync_engine.sync_cleaned_column(df, col)
                        st.success(result["message"])
                        break
                else:
                    st.warning("No suitable tag column found")

    with tab3:
        st.subheader("📋 Sync History")
        history = st.session_state.get("notion_sync_history", [])
        if history:
            for entry in reversed(history[-20:]):
                ts = entry.get("timestamp", "")
                stype = entry.get("type", "").replace("_", " ").title()
                result = entry.get("result", {})
                status = "✅" if result.get("success") else "âŒ"
                st.markdown(f"{status} **{ts}**  {stype}: {result.get('message', '')}")
        else:
            st.info("No sync history yet.")

