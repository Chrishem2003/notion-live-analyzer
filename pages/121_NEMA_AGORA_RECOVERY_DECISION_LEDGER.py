"""Phase 113 — Recovery Decision Ledger demo."""
import tempfile,streamlit as st
from nema_agora.api_governance_drift_recovery_review_ledger import review_recovery_recommendation
from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
from nema_agora.api_governance_drift_recovery_review_lifecycle import evaluate_recovery_review
from nema_agora.api_governance_drift_recovery_decision_ledger import authorize_recovery_decision,RecoveryDecisionLedger
st.set_page_config(page_title="NEMA-AGORA Recovery Decision Ledger",layout="wide")
st.title("NEMA-AGORA — Recovery Decision Ledger")
r=build_history_integrity_monitor([],expected_count=0,observed_at="2026-10-04T12:00:00+00:00")
v=review_recovery_recommendation(r,actor_id="demo-reviewer",role="coordinator",outcome="NO_ACTION_APPROVED",reviewed_at="2026-10-04T12:01:00+00:00")
l=evaluate_recovery_review(v,evaluated_at="2026-10-04T12:02:00+00:00")
d=authorize_recovery_decision(l,actor_id="demo-admin",role="admin",decision="AUTHORIZE_NO_ACTION",decided_at="2026-10-04T12:03:00+00:00",rationale="Synthetic demonstration.")
with tempfile.TemporaryDirectory() as tmp:
 led=RecoveryDecisionLedger(tmp+"/decisions.db"); stored=led.append(d)
st.metric("Decision",stored["decision"]); st.metric("Execution permitted",str(stored["execution_permitted"])); st.json(stored)
st.info("Synthetic evidence only. Authorization is recorded but no recovery is executed.")
