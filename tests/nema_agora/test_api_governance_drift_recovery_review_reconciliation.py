import pytest
from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_review_ledger import review_recovery_recommendation
from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
from nema_agora.api_governance_drift_recovery_review_reconciliation import reconcile_recovery_reviews

def monitor(): return build_history_integrity_monitor([], expected_count=0, observed_at='2026-10-04T12:00:00+00:00')
def reviewed(report=None, outcome='BACKUP_REVIEWED'):
    report=report or monitor()
    return review_recovery_recommendation(report, actor_id='reviewer-01', role='coordinator', outcome=outcome, reviewed_at='2026-10-04T12:10:00+00:00', notes='reviewed')

def test_valid_reconciliation():
    report=monitor(); result=reconcile_recovery_reviews([report],[reviewed(report)],expected_ledger_count=1)
    assert result['state']=='RECONCILED'; assert result['findings']==[]; assert result['read_only'] is True
    assert result['reconciliation_fingerprint']==fingerprint({k:v for k,v in result.items() if k!='reconciliation_fingerprint'})

def test_missing_review_is_control_required():
    result=reconcile_recovery_reviews([monitor()],[],expected_ledger_count=0); assert result['state']=='CONTROL_REQUIRED'; assert any(x['code']=='UNREVIEWED_MONITOR_REPORT' for x in result['findings'])

def test_orphan_review_is_detected():
    report=monitor(); review=reviewed(report); review['monitor_fingerprint']='0'*64
    result=reconcile_recovery_reviews([report],[review]); assert any(x['code']=='INVALID_RECOVERY_REVIEW' for x in result['findings'])

def test_tampered_monitor_is_detected():
    report=monitor(); report['recovery_recommendation']='PRESERVE_AND_ESCALATE'; result=reconcile_recovery_reviews([report],[]); assert any(x['code']=='INVALID_MONITOR_REPORT' for x in result['findings'])

def test_duplicate_monitor_is_detected():
    report=monitor(); result=reconcile_recovery_reviews([report,report],[reviewed(report)]); assert any(x['code']=='DUPLICATE_MONITOR_FINGERPRINT' for x in result['findings'])

def test_policy_mismatch_is_detected():
    report=monitor(); review=reviewed(report); review['policy_version']='wrong'
    payload={k:review[k] for k in ('monitor_fingerprint','monitor_state','recovery_recommendation','reviewer_actor_id','reviewer_role','outcome','reviewed_at','notes')}
    review['audit_fingerprint']=fingerprint(payload); review['review_audit_id']='NEMA-AGORA-RECOVERY-REVIEW-'+review['audit_fingerprint'][:24]
    result=reconcile_recovery_reviews([report],[review]); assert any(x['code']=='REVIEW_POLICY_MISMATCH' for x in result['findings'])

def test_ledger_count_mismatch():
    report=monitor(); result=reconcile_recovery_reviews([report],[reviewed(report)],expected_ledger_count=2); assert any(x['code']=='LEDGER_COUNT_MISMATCH' for x in result['findings'])

def test_no_action_is_blocked_for_no_history():
    with pytest.raises(ValueError,match='NO_ACTION_NOT_ALLOWED_WITHOUT_HISTORY'): reviewed(monitor(),outcome='NO_ACTION_APPROVED')

def test_deterministic_result():
    report=monitor(); reviews=[reviewed(report)]; assert reconcile_recovery_reviews([report],reviews,expected_ledger_count=1)==reconcile_recovery_reviews([report],reviews,expected_ledger_count=1)
