"""NEMA-AGORA Phase 105 — persistent governance drift review audit registry demo."""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from nema_agora.api_governance_drift_human_review import review_drift
from nema_agora.api_governance_drift_review_registry import (
    GovernanceDriftReviewAuditRegistry,
    POLICY_VERSION,
)

st.set_page_config(page_title="NEMA-AGORA Phase 105", layout="wide")
st.title("NEMA-AGORA — Governance Drift Review Audit Registry")
st.caption("Phase 105 • persistent, append-only human-review evidence")

st.warning(
    "Evidence infrastructure only. This prototype does not establish environmental "
    "truth, regulatory status, NEMA authorization, enforcement authority, or emergency action."
)

item = {
    "review_id": "API-DRIFT-REVIEW-DEMO",
    "drift_id": "API-DRIFT-DEMO",
    "drift_fingerprint": "a" * 64,
    "baseline_snapshot_id": "API-SNAPSHOT-BASE-DEMO",
    "current_snapshot_id": "API-SNAPSHOT-CURRENT-DEMO",
    "state": "QUEUED",
}
audit = review_drift(
    item,
    actor_id="demo-coordinator",
    role="coordinator",
    outcome="ACKNOWLEDGED",
    reviewed_at="2026-10-04T12:00:00Z",
)

with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / "phase105.db"
    registry = GovernanceDriftReviewAuditRegistry(db)
    stored = registry.append(audit)
    rows = registry.list()

    st.subheader("Registry contract")
    st.json({
        "policy_version": POLICY_VERSION,
        "state": "APPEND_ONLY",
        "records": len(rows),
        "audit_id": stored["audit_id"],
        "review_id": stored["review_id"],
        "drift_id": stored["drift_id"],
        "reviewer": stored["reviewer_actor_id"],
        "outcome": stored["outcome"],
        "audit_fingerprint": stored["audit_fingerprint"],
    })

st.info(
    "The demonstration uses synthetic evidence. A production deployment would "
    "require an approved identity, persistence, retention and operational security design."
)
