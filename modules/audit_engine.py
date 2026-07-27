import hashlib
import json
from datetime import datetime

def generate_compliance_hash(data):
    """Generates a SHA-256 compliance checksum hash for audit logs or data dictionaries."""
    if isinstance(data, (dict, list)):
        serialized = json.dumps(data, sort_keys=True, default=str)
    else:
        serialized = str(data)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def format_audit_log(event_name, user_id, details=None):
    """Formats a structured audit log entry."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_name,
        "user": user_id,
        "details": details or {},
        "hash": generate_compliance_hash(details or {})
    }
