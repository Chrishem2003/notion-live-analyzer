"""NEMA-AGORA Phase 110 — synthetic human recovery review ledger demo."""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
from nema_agora.api_governance_drift_recovery_review_ledger import (
    RecoveryReviewLedger,
    review_recovery_recommendation,
)

st.set_page_config(page_title="NEMA-AGORA Phase 110", layout="wide")
st.title("NEMA-AGORA — Human-Acknowledged Recovery Review")
st.caption("Phase 110 • authorized review evidence • append-only ledger")
st.warning(
    "Synthetic demonstration only. This is not an official NEMA system. "
    "Recording a review does not restore or repair any database and creates no environmental or regulatory conclusion."
)

if "phase110_demo_dir" not in st.session_state:
    st.session_state["phase110_demo_dir"] = tempfile.mkdtemp(prefix="nema_agora_phase110_")
ledger = RecoveryReviewLedger(Path(st.session_state["phase110_demo_dir"]) / "synthetic_reviews.db")
report = build_history_integrity_monitor(
    [], expected_count=0, observed_at="2026-10-04T14:00:00Z"
)
st.subheader("Synthetic Phase 109 monitor report")
a, b, c = st.columns(3)
a.metric("Monitor state", report["state"])
b.metric("Recommendation", report["recovery_recommendation"])
c.metric("Existing review records", ledger.count())
st.code(report["monitor_fingerprint"])

with st.form("phase110_review_form"):
    actor_id = st.text_input("Reviewer identifier", value="demo-coordinator")
    role = st.selectbox("Reviewer role", ["coordinator", "admin"])
    outcome = st.selectbox(
        "Review outcome",
        ["ACKNOWLEDGED", "BACKUP_REVIEWED", "RECOVERY_DEFERRED", "ESCALATED", "NO_ACTION_APPROVED"],
    )
    notes = st.text_area("Review notes", value="Synthetic demonstration review only.")
    submitted = st.form_submit_button("Record human review")
if submitted:
    try:
        review = review_recovery_recommendation(
            report,
            actor_id=actor_id,
            role=role,
            outcome=outcome,
            reviewed_at="2026-10-04T15:00:00Z",
            notes=notes,
        )
        saved = ledger.append(review)
        st.success(f"Review recorded: {saved['review_audit_id']}")
    except ValueError as exc:
        st.error(f"Review not recorded: {exc}")

st.subheader("Append-only review history")
records = ledger.list()
if records:
    st.dataframe(
        [
            {
                "review_audit_id": item["review_audit_id"],
                "reviewer_actor_id": item["reviewer_actor_id"],
                "reviewer_role": item["reviewer_role"],
                "outcome": item["outcome"],
                "reviewed_at": item["reviewed_at"],
                "audit_fingerprint": item["audit_fingerprint"],
            }
            for item in records
        ],
        use_container_width=True,
    )
else:
    st.info("No human review has been recorded in this temporary demo ledger yet.")
st.caption("Temporary synthetic database only. No automatic recovery operation is available in this phase.")
