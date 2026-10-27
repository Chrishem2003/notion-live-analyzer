"""Phase 104 — governance drift human review and audit binding."""
from __future__ import annotations
from typing import Any,Mapping
from .api_audit_binding import fingerprint
OUTCOMES=("ACKNOWLEDGED","INVESTIGATE","NO_DRIFT_CONFIRMED","ESCALATED")
ROLES=("coordinator","admin")
POLICY_VERSION="phase104-v1"
def review_drift(item:Mapping[str,Any],*,actor_id:str,role:str,outcome:str,reviewed_at:str)->dict[str,Any]:
 if item.get("state")!="QUEUED": raise ValueError("REVIEW_ITEM_NOT_QUEUED")
 if not actor_id or role not in ROLES: raise ValueError("REVIEWER_NOT_AUTHORIZED")
 if outcome not in OUTCOMES: raise ValueError("INVALID_REVIEW_OUTCOME")
 if not reviewed_at.strip(): raise ValueError("REVIEW_TIME_REQUIRED")
 payload={"review_id":item["review_id"],"drift_id":item["drift_id"],"drift_fingerprint":item["drift_fingerprint"],"baseline_snapshot_id":item["baseline_snapshot_id"],"current_snapshot_id":item["current_snapshot_id"],"reviewer_actor_id":actor_id,"reviewer_role":role,"outcome":outcome,"reviewed_at":reviewed_at}
 return dict(payload,audit_id="API-DRIFT-REVIEW-AUDIT-"+fingerprint(payload)[:24],audit_fingerprint=fingerprint(payload),state="REVIEW_RECORDED",policy_version=POLICY_VERSION,interpretation="API_GOVERNANCE_DRIFT_HUMAN_REVIEW",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None)
