"""Phase 112 — Recovery Review Snapshot History demonstration using synthetic data only."""
from __future__ import annotations

import tempfile
import streamlit as st

from nema_agora.api_governance_drift_recovery_review_ledger import review_recovery_recommendation
from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
from nema_agora.api_governance_drift_recovery_review_reconciliation import reconcile_recovery_reviews
from nema_agora.api_governance_drift_recovery_review_history import build_recovery_review_snapshot
from nema_agora.api_governance_drift_recovery_review_history_registry import RecoveryReviewSnapshotHistoryRegistry

st.set_page_config(page_title="NEMA-AGORA Recovery Review Snapshot History", layout="wide")
st.title("NEMA-AGORA — Recovery Review Snapshot History")
st.caption("Phase 112 • append-only evidence history • synthetic demonstration")

report = build_history_integrity_monitor([], expected_count=0, observed_at="2026-10-10T09:00:00Z")
review = review_recovery_recommendation(
    report, actor_id="demo-reviewer", role="coordinator", outcome="BACKUP_REVIEWED",
    reviewed_at="2026-10-10T09:10:00Z", notes="Synthetic demonstration only."
)
review["ledger_policy_version"] = "phase110-v1"
reconciliation = reconcile_recovery_reviews([report], [review], expected_ledger_count=1)

with tempfile.TemporaryDirectory() as tmp:
    registry = RecoveryReviewSnapshotHistoryRegistry(f"{tmp}/recovery_review_history.db")
    snapshot = build_recovery_review_snapshot(
        reconciliation, captured_at="2026-10-10T09:20:00Z", sequence=1
    )
    registry.append(snapshot)
    integrity = registry.integrity_report()

left, middle, right = st.columns(3)
left.metric("History state", integrity["state"])
middle.metric("Snapshots", integrity["snapshot_count"])
right.metric("Findings", integrity["finding_count"])
st.subheader("Snapshot history integrity")
st.json(integrity)
st.caption("Synthetic records only. This page does not repair data or execute recovery.")
