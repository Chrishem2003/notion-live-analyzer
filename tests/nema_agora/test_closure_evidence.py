from nema_agora.closure_evidence import ClosureEvidenceRegistry, evaluate_with_registry, build_operational_report
from nema_agora.governance_exception_resolution import GovernanceExceptionResolver

def rec(fp='fp-1'):
    return {'status':'CONTROL_REQUIRED','reconciliation_fingerprint':fp,'exceptions':[{'code':'MISSING_AUDIT_EVENT','severity':'CRITICAL','decision_kind':'review_decision','artifact_id':'REV-1','detail':'missing'}]}

def test_registry_requires_verified_current_binding(tmp_path):
    path=tmp_path/'db.sqlite'; registry=ClosureEvidenceRegistry(path); resolver=GovernanceExceptionResolver(path)
    resolution=resolver.resolve(exception_code='MISSING_AUDIT_EVENT',decision_kind='review_decision',artifact_id='REV-1',actor_id='u1',role='reviewer',outcome='CORRECTED_AT_SOURCE',reason_code='FIXED',reconciliation_fingerprint='fp-1')
    event_id=resolution.get('entry_id') or resolution.get('event_id')
    registry.register(evidence_id='E1',evidence_hash='a'*64,evidence_type='SOURCE_CORRECTION',reconciliation_fingerprint='fp-1',exception_code='MISSING_AUDIT_EVENT',decision_kind='review_decision',artifact_id='REV-1',resolution_event_id=event_id,provenance_ref='PROV-1',registered_by='u1')
    assert evaluate_with_registry(rec(),resolver.list_resolutions(),registry.list())['results'][0]['status']=='REVIEW_REQUIRED'
    registry.register(evidence_id='E2',evidence_hash='b'*64,evidence_type='SOURCE_CORRECTION',reconciliation_fingerprint='fp-1',exception_code='MISSING_AUDIT_EVENT',decision_kind='review_decision',artifact_id='REV-1',resolution_event_id=event_id,provenance_ref='PROV-2',registered_by='u1',verification_state='VERIFIED')
    result=evaluate_with_registry(rec(),resolver.list_resolutions(),registry.list())
    assert result['results'][0]['status']=='CLOSED'
    assert result['results'][0]['evidence_provenance']['provenance_ref']=='PROV-2'

def test_stale_fingerprint_never_closes(tmp_path):
    path=tmp_path/'db.sqlite'; registry=ClosureEvidenceRegistry(path); resolver=GovernanceExceptionResolver(path)
    resolution=resolver.resolve(exception_code='MISSING_AUDIT_EVENT',decision_kind='review_decision',artifact_id='REV-1',actor_id='u1',role='reviewer',outcome='FALSE_POSITIVE',reason_code='CHECKED',reconciliation_fingerprint='fp-1')
    registry.register(evidence_id='OLD',evidence_hash='c'*64,evidence_type='FALSE_POSITIVE_REVIEW',reconciliation_fingerprint='old-fp',exception_code='MISSING_AUDIT_EVENT',decision_kind='review_decision',artifact_id='REV-1',resolution_event_id=resolution.get('entry_id') or resolution.get('event_id'),provenance_ref='PROV-OLD',registered_by='u1',verification_state='VERIFIED')
    result=evaluate_with_registry(rec('new-fp'),resolver.list_resolutions(),registry.list())
    assert result['results'][0]['status']=='OPEN'

def test_operational_report_counts():
    closure={'reconciliation_fingerprint':'fp','results':[{'status':'CLOSED','closure_code':'CLOSURE_EVIDENCE_ACCEPTED','severity':'CRITICAL'},{'status':'REVIEW_REQUIRED','closure_code':'MISSING_CLOSURE_EVIDENCE','severity':'CRITICAL'},{'status':'CONTROL_REQUIRED','closure_code':'ESCALATED_REMAINS_OPEN','severity':'CRITICAL'},{'status':'OPEN','closure_code':'NO_RESOLUTION','severity':'CRITICAL'}]}
    r=build_operational_report(closure,evidence_rows=[],resolutions=[])
    assert (r['total_exceptions'],r['closed'],r['review_required'],r['control_required'],r['open'],r['missing_evidence'],r['unresolved_critical'])==(4,1,1,1,1,1,3)
