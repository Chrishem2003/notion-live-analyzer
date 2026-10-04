"""Phase 111 — Recovery Review Reconciliation demo."""
from __future__ import annotations
import tempfile
import streamlit as st
from nema_agora.api_governance_drift_recovery_review_ledger import RecoveryReviewLedger, review_recovery_recommendation
from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
from nema_agora.api_governance_drift_recovery_review_reconciliation import reconcile_recovery_reviews
st.set_page_config(page_title='NEMA-AGORA Recovery Review Reconciliation',layout='wide')
st.title('NEMA-AGORA — Recovery Review Reconciliation')
st.caption('Phase 111 • read-only synthetic governance evidence • independent prototype')
report=build_history_integrity_monitor([],expected_count=0,observed_at='2026-10-04T12:00:00+00:00')
review=review_recovery_recommendation(report,actor_id='demo-reviewer',role='coordinator',outcome='BACKUP_REVIEWED',reviewed_at='2026-10-04T12:10:00+00:00',notes='Synthetic demonstration review.')
with tempfile.TemporaryDirectory() as tmp:
    ledger=RecoveryReviewLedger(f'{tmp}/recovery_reviews.db')
    stored=ledger.append(review)
    result=reconcile_recovery_reviews([report],[stored],expected_ledger_count=ledger.count())
c1,c2,c3=st.columns(3); c1.metric('State',result['state']); c2.metric('Findings',len(result['findings'])); c3.metric('Read only',str(result['read_only']))
st.subheader('Reconciliation evidence'); st.json(result)
st.info('Synthetic evidence only. No recovery, environmental, regulatory, enforcement, or emergency action is performed.')
