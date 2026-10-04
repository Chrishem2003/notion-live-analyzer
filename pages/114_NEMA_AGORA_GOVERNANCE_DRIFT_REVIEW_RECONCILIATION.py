"""NEMA-AGORA Phase 106 — governance drift review reconciliation demo."""
from __future__ import annotations

import streamlit as st

from nema_agora.api_governance_drift_human_review import review_drift
from nema_agora.api_governance_drift_review_reconciliation import reconcile_drift_reviews

st.set_page_config(page_title="NEMA-AGORA Phase 106", layout="wide")
st.title("NEMA-AGORA — Drift Review Audit Reconciliation")
st.caption("Phase 106 • read-only evidence integrity control")

st.warning(
    "Synthetic demonstration only. This reconciliation does not establish environmental "
    "truth, regulatory status, NEMA authorization, enforcement or emergency action."
)

drift = {
    "drift_id": "API-DRIFT-DEMO",
    "drift_fingerprint": "a" * 64,
    "baseline_snapshot_id": "API-SNAPSHOT-BASE-DEMO",
    "current_snapshot_id": "API-SNAPSHOT-CURRENT-DEMO",
    "state": "REVIEW_TRIGGERED",
}
queue = {
    "review_id": "API-DRIFT-REVIEW-DEMO",
    "drift_id": drift["drift_id"],
    "drift_fingerprint": drift["drift_fingerprint"],
    "baseline_snapshot_id": drift["baseline_snapshot_id"],
    "current_snapshot_id": drift["current_snapshot_id"],
    "state": "QUEUED",
}
audit = review_drift(
    queue, actor_id="demo-coordinator", role="coordinator",
    outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:00:00Z",
)
result = reconcile_drift_reviews([queue], [drift], [audit], [dict(audit, policy_version="phase105-v1")])

col1, col2, col3, col4 = st.columns(4)
col1.metric("State", result["state"])
col2.metric("Queue items", result["queue_count"])
col3.metric("Human audits", result["review_audit_count"])
col4.metric("Persisted rows", result["persisted_audit_count"])
st.subheader("Reconciliation findings")
if result["findings"]:
    st.dataframe(result["findings"], use_container_width=True)
else:
    st.success("No findings in this synthetic fixture.")
st.code(result["reconciliation_fingerprint"])
st.caption("Demo registry row is synthetic; no live operational database is connected.")
