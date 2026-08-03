import security_guard
import security_guard

import json
import logging
from modules.api_safeguards import safe_api_request

logger = logging.getLogger("Notifier")

def send_backup_webhook_alert(webhook_url: str, record_count: int, db_id: str, platform: str = "discord"):
    """
    Dispatches a structured webhook alert when a database snapshot finishes.
    Supports Discord and Slack webhook payloads.
    """
    if not webhook_url:
        return False

    title = "ðŸ’¾ Notion Database Backup Completed"
    description = f"Successfully snapshotted Notion DB `{db_id}` with **{record_count} records**."

    if "discord.com" in webhook_url:
        payload = {
            "embeds": [{
                "title": title,
                "description": description,
                "color": 3066993,  # Green accent
                "footer": {"text": "Notion Live Research Analyzer"}
            }]
        }
    else:
        # Standard Slack-compatible webhook format
        payload = {
            "text": f"*{title}*\n{description}"
        }

    try:
        response = safe_api_request(
            method="POST",
            url=webhook_url,
            json_data=payload,
            timeout=5,
            service_type="generic"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch webhook alert: {e}")
        return False
