"""Audit Logger  Session & Event Telemetry Engine."""
import streamlit as st
from datetime import datetime
from typing import Dict, Any, List

def init_audit_log():
    """Initialize the audit log in session state."""
    if "audit_log" not in st.session_state:
        st.session_state["audit_log"] = []

def log_event(event_type: str, details: Dict[str, Any] = None):
    """
    Log an event to the in-memory audit trail.
    Records: timestamp, event_type, details
    """
    init_audit_log()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "details": details or {}
    }
    st.session_state["audit_log"].append(entry)

def get_audit_log() -> List[Dict]:
    """Retrieve the full audit log."""
    init_audit_log()
    return st.session_state["audit_log"]

def clear_audit_log():
    """Clear the audit log."""
    st.session_state["audit_log"] = []

def export_audit_log() -> str:
    """Export audit log as a formatted string."""
    log = get_audit_log()
    if not log:
        return "No audit events recorded."
    
    lines = ["=== AUDIT LOG ===", ""]
    for entry in log:
        ts = entry.get("timestamp", "")
        et = entry.get("event_type", "")
        details = entry.get("details", {})
        detail_str = ", ".join(f"{k}={v}" for k, v in details.items()) if details else ""
        lines.append(f"[{ts}] {et} {detail_str}")
    return "\n".join(lines)