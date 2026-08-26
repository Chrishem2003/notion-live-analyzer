
import requests
import json
from datetime import datetime
from modules.database import log_backend_event

def send_enterprise_webhook(webhook_url: str, event_type: str, message: str, payload_data: dict = None):
    """
    Dispatches a standardized JSON payload to any registered webhook URL (Slack, Discord, Custom API).
    """
    if not webhook_url or webhook_url.startswith("https://your-webhook-endpoint"):
        return {"status": "skipped", "reason": "Invalid or default webhook URL provided."}

    payload = {
        "timestamp": datetime.now().isoformat(),
        "source": "CHRISHEM Enterprise Intelligence Engine",
        "event_type": event_type,
        "message": message,
        "data": payload_data or {}
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ChrishemEngine-WebhookDispatcher/1.0"
    }

    try:
        response = requests.post(webhook_url, data=json.dumps(payload), headers=headers, timeout=5)
        if response.status_code in [200, 201, 204]:
            log_backend_event("INFO", f"Webhook dispatched successfully to {webhook_url[:30]}...")
            return {"status": "success", "status_code": response.status_code}
        else:
            log_backend_event("WARNING", f"Webhook dispatch returned status code {response.status_code}")
            return {"status": "failed", "status_code": response.status_code}
    except Exception as e:
        log_backend_event("ERROR", f"Webhook dispatch exception: {str(e)}")
        return {"status": "error", "message": str(e)}

