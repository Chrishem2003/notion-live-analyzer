
import requests
from modules.database import log_backend_event

def dispatch_system_alert(webhook_url: str, message: str):
    """
    Dispatches a real-time notification alert via webhook (Discord/Telegram/n8n).
    """
    if not webhook_url or webhook_url == "https://your-webhook-endpoint":
        return False
    
    payload = {"content": f"? **CHRISHEM Engine Alert**: {message}"}
    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        if response.status_code in [200, 204]:
            log_backend_event("INFO", "Webhook alert dispatched successfully.")
            return True
    except Exception as e:
        log_backend_event("ERROR", f"Webhook dispatch failed: {str(e)}")
    return False

