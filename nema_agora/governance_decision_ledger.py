"""Phase 38 — governed decision ledger integration.

Provides one narrow adapter for connecting real application decision boundaries
to the Phase 36 governed audit-event layer. It records metadata only, requires
an authenticated actor/role, and preserves idempotency. It never makes or
changes a governance decision.
"""
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping
from nema_agora.audit_events import AuditEventCapture
from nema_agora.audit_ledger import AuditLedger

POLICY_VERSION = "phase38-v1"
EVENT_MAP = {
    "evaluation_completed": ("EVALUATION_COMPLETED", "evaluation"),
    "review_decision": ("REVIEW_DECISION_RECORDED", "review"),
    "lifecycle_decision": ("MODEL_LIFECYCLE_DECIDED", "model_governance"),
    "backup_verification": ("BACKUP_VERIFICATION_COMPLETED", "audit_recovery"),
    "access_denied": ("ACCESS_POLICY_DENIED", "access_control"),
}

def _id(prefix: str, material: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(dict(material), sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:40].upper()
    return f"{prefix}-{digest}"

class GovernanceDecisionLedger:
    """Record already-made governance decisions in the governed audit ledger."""

    def __init__(self, database_path: str):
        self.ledger = AuditLedger(database_path)
        self.capture = AuditEventCapture(self.ledger)

    def record(self, *, decision_kind: str, actor_id: str, role: str,
               artifact_id: str, status: str, decision: str,
               reason_code: str, counts: Mapping[str, int] | None = None) -> dict[str, Any]:
        if decision_kind not in EVENT_MAP:
            raise ValueError("Unsupported governance decision kind.")
        event_type, source_module = EVENT_MAP[decision_kind]
        if not isinstance(artifact_id, str) or not artifact_id.strip():
            raise ValueError("Explicit artifact_id is required.")
        payload: dict[str, Any] = {
            "artifact_id": artifact_id.strip(),
            "status": status,
            "decision": decision,
            "reason_code": reason_code,
            "source_module": source_module,
            "recorded_by_role": role,
            "policy_version": POLICY_VERSION,
        }
        if counts is not None:
            payload["counts"] = dict(counts)
        # One artifact represents one governed decision boundary. Reusing
        # the same identity with changed outcome metadata must fail rather than
        # create a second history for the same boundary.
        event_id = _id("GOV", {
            "decision_kind": decision_kind, "artifact_id": artifact_id.strip(),
        })
        return self.capture.record(
            event_id=event_id, event_type=event_type, actor_id=actor_id, payload=payload
        )
