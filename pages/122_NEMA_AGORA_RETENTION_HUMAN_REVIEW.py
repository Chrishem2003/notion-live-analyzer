"""Phase 118 — synthetic retention human-review demonstration."""
import streamlit as st

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_review import review_retention_health

st.set_page_config(page_title="NEMA-AGORA Retention Human Review", layout="wide")
st.title("NEMA-AGORA — Authorization Retention Human Review")

monitor_payload = {
    "policy_version": "phase117-v1",
    "observed_at": "2026-10-04T12:00:00+00:00",
    "registry_policy_version": "phase116-v1",
    "state": "RETENTION_HEALTHY",
    "snapshot_count": 1,
    "valid_snapshot_count": 1,
    "expected_count": 1,
    "history_state": "HISTORY_READY",
    "history_reconciliation_fingerprint": "synthetic-history",
    "findings": [],
    "retention_recommendation": "NO_RETENTION_ACTION",
    "read_only": True,
    "automatic_repair_performed": False,
    "execution_gate_closed": True,
    "interpretation": "AUTHORIZATION_RETENTION_INTEGRITY_MONITORING",
    "environmental_conclusion": None,
    "regulatory_conclusion": None,
    "enforcement_action": None,
}
monitor = dict(monitor_payload, monitor_fingerprint=fingerprint(monitor_payload))
review = review_retention_health(
    monitor,
    actor_id="demo-reviewer",
    role="coordinator",
    outcome="ACKNOWLEDGED",
    reviewed_at="2026-10-04T12:01:00+00:00",
    notes="Synthetic demonstration only.",
)

st.metric("Monitor state", monitor["state"])
st.metric("Human review", review["outcome"])
st.metric("Execution gate closed", str(review["execution_gate_closed"]))
st.json(review)
st.info("Synthetic evidence only. No retention repair or external action is executed.")
