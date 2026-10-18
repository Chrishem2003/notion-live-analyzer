"""Phase 111 — read-only reconciliation of recovery-review evidence."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_review_ledger import (
    POLICY_VERSION as LEDGER_POLICY_VERSION,
    validate_recovery_review,
    validate_monitor_report,
)

POLICY_VERSION = "phase111-v1"
MONITOR_POLICY_VERSION = "phase109-v1"

def reconcile_recovery_reviews(monitor_reports: Sequence[Mapping[str, Any]], review_records: Sequence[Mapping[str, Any]], *, expected_ledger_count: int | None = None) -> dict[str, Any]:
    """Reconcile Phase 109 monitor reports against Phase 110 human-review evidence."""
    if not isinstance(monitor_reports, Sequence) or isinstance(monitor_reports, (str, bytes)): raise ValueError('INVALID_MONITOR_REPORTS')
    if not isinstance(review_records, Sequence) or isinstance(review_records, (str, bytes)): raise ValueError('INVALID_REVIEW_RECORDS')
    if expected_ledger_count is not None and (not isinstance(expected_ledger_count, int) or isinstance(expected_ledger_count, bool) or expected_ledger_count < 0): raise ValueError('INVALID_EXPECTED_LEDGER_COUNT')
    reports, reviews = list(monitor_reports), list(review_records)
    findings=[]; valid_reports=[]; valid_reviews=[]
    report_fps=[]; review_ids=[]; review_fps=[]
    for i, report in enumerate(reports):
        if not isinstance(report, Mapping): findings.append({'code':'INVALID_MONITOR_REPORT','index':i}); continue
        try:
            x=validate_monitor_report(report); valid_reports.append(x); report_fps.append(x['monitor_fingerprint'])
        except ValueError as exc: findings.append({'code':'INVALID_MONITOR_REPORT','index':i,'reason':str(exc)})
    for i, review in enumerate(reviews):
        if not isinstance(review, Mapping): findings.append({'code':'INVALID_RECOVERY_REVIEW','index':i}); continue
        try:
            x=validate_recovery_review(review); valid_reviews.append(x); review_ids.append(x['review_audit_id']); review_fps.append(x['audit_fingerprint'])
        except ValueError as exc: findings.append({'code':'INVALID_RECOVERY_REVIEW','index':i,'reason':str(exc)})
    for value,count in Counter(report_fps).items():
        if count>1: findings.append({'code':'DUPLICATE_MONITOR_FINGERPRINT','identity':value})
    for value,count in Counter(review_ids).items():
        if count>1: findings.append({'code':'DUPLICATE_REVIEW_AUDIT_ID','identity':value})
    for value,count in Counter(review_fps).items():
        if count>1: findings.append({'code':'DUPLICATE_REVIEW_AUDIT_FINGERPRINT','identity':value})
    report_by_fp={x['monitor_fingerprint']:x for x in valid_reports}
    review_by_fp={}
    for x in valid_reviews: review_by_fp.setdefault(x['monitor_fingerprint'],[]).append(x)
    for fp,report in report_by_fp.items():
        bound=review_by_fp.get(fp,[])
        if not bound: findings.append({'code':'UNREVIEWED_MONITOR_REPORT','monitor_fingerprint':fp}); continue
        if len(bound)>1: findings.append({'code':'MULTIPLE_REVIEWS_FOR_MONITOR','monitor_fingerprint':fp})
        for review in bound:
            if review['monitor_state']!=report['state']: findings.append({'code':'REVIEW_MONITOR_STATE_MISMATCH','monitor_fingerprint':fp,'observed':review['monitor_state'],'expected':report['state']})
            if review['recovery_recommendation']!=report['recovery_recommendation']: findings.append({'code':'REVIEW_RECOMMENDATION_MISMATCH','monitor_fingerprint':fp,'observed':review['recovery_recommendation'],'expected':report['recovery_recommendation']})
            if review.get('policy_version')!=LEDGER_POLICY_VERSION: findings.append({'code':'REVIEW_POLICY_MISMATCH','monitor_fingerprint':fp,'observed':review.get('policy_version'),'expected':LEDGER_POLICY_VERSION})
            if review.get('state')!='REVIEW_RECORDED': findings.append({'code':'REVIEW_STATE_MISMATCH','monitor_fingerprint':fp,'observed':review.get('state')})
            if review.get('automatic_recovery_performed') is not False: findings.append({'code':'AUTOMATIC_RECOVERY_FLAG_MISMATCH','monitor_fingerprint':fp})
            if any(review.get(k) is not None for k in ('environmental_conclusion','regulatory_conclusion','enforcement_action')): findings.append({'code':'UNEXPECTED_GOVERNANCE_CONCLUSION_FIELD','monitor_fingerprint':fp})
            if report['state'] in ('CONTROL_REQUIRED','NO_HISTORY') and review['outcome']=='NO_ACTION_APPROVED': findings.append({'code':'INVALID_NO_ACTION_OUTCOME','monitor_fingerprint':fp,'state':report['state']})
    for review in valid_reviews:
        if review['monitor_fingerprint'] not in report_by_fp: findings.append({'code':'ORPHAN_RECOVERY_REVIEW','monitor_fingerprint':review['monitor_fingerprint'],'review_audit_id':review['review_audit_id']})
        if review.get('ledger_policy_version')!=LEDGER_POLICY_VERSION: findings.append({'code':'LEDGER_POLICY_MISMATCH','review_audit_id':review['review_audit_id'],'observed':review.get('ledger_policy_version'),'expected':LEDGER_POLICY_VERSION})
    if expected_ledger_count is not None and expected_ledger_count!=len(reviews): findings.append({'code':'LEDGER_COUNT_MISMATCH','expected':expected_ledger_count,'observed':len(reviews)})
    findings.sort(key=lambda x:(x.get('code',''),str(x.get('index','')),str(x.get('monitor_fingerprint','')),str(x.get('review_audit_id','')),str(x.get('identity',''))))
    state='CONTROL_REQUIRED' if findings else 'RECONCILED'
    payload={'policy_version':POLICY_VERSION,'monitor_policy_version':MONITOR_POLICY_VERSION,'ledger_policy_version':LEDGER_POLICY_VERSION,'state':state,'monitor_report_count':len(reports),'valid_monitor_report_count':len(valid_reports),'review_record_count':len(reviews),'valid_review_record_count':len(valid_reviews),'expected_ledger_count':expected_ledger_count,'findings':findings,'read_only':True,'interpretation':'RECOVERY_REVIEW_RECONCILIATION','environmental_conclusion':None,'regulatory_conclusion':None,'enforcement_action':None}
    return dict(payload,reconciliation_fingerprint=fingerprint(payload))
