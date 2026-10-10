"""Phase 112 — Recovery Review Lifecycle demo."""
import streamlit as st
from nema_agora.api_governance_drift_recovery_review_ledger import review_recovery_recommendation
from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
from nema_agora.api_governance_drift_recovery_review_reconciliation import reconcile_recovery_reviews
from nema_agora.api_governance_drift_recovery_review_lifecycle import build_recovery_review_lifecycle
st.set_page_config(page_title="NEMA-AGORA Recovery Review Lifecycle",layout="wide")
st.title("NEMA-AGORA — Recovery Review Lifecycle")
report=build_history_integrity_monitor([],expected_count=0,observed_at="2026-10-04T12:00:00+00:00")
review=review_recovery_recommendation(report,actor_id="demo-reviewer",role="coordinator",outcome="BACKUP_REVIEWED",reviewed_at="2026-10-04T12:10:00+00:00",notes="Synthetic lifecycle review.")
recon=reconcile_recovery_reviews([report],[review],expected_ledger_count=1)
snapshot=build_recovery_review_lifecycle(recon,[review],evaluated_at="2026-10-04T12:20:00+00:00")
st.metric("Lifecycle state",snapshot["lifecycles"][0]["lifecycle_state"])
st.json(snapshot)
st.info("Synthetic evidence only. Lifecycle evaluation never executes recovery or regulatory/enforcement action.")
