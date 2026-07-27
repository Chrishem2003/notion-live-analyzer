import hashlib
import json
from datetime import datetime

def generate_compliance_hash(record_data: dict) -> str:
    """Generates a SHA-256 cryptographic hash for data provenance and FAIR compliance."""
    serialized = json.dumps(record_data, sort_keys=True)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

def format_audit_log(user_id: str, action: str, target_db: str, hash_val: str):
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "actor": user_id,
        "action": action,
        "database_target": target_db,
        "sha256_provenance": hash_val,
        "fair_compliant": True
    }
