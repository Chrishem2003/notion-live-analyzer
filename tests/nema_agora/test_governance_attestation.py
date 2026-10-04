from nema_agora.closure_evidence import ClosureEvidenceRegistry
from nema_agora.governance_exception_resolution import GovernanceExceptionResolver
from nema_agora.governance_attestation import (
    GovernanceAttestationRegistry, verify_evidence_integrity,
    build_provenance_completeness, build_integrity_snapshot, ATTESTED, STALE, CONTROL_REQUIRED,
)

def _rec(fp="fp-1"):
    return {"reconciliation_fingerprint":fp,"exceptions":[
        {"code":"MISSING_AUDIT_EVENT","severity":"CRITICAL","decision_kind":"review_decision","artifact_id":"REV-1"}
    ]}

def _evidence(path, fp="fp-1"):
    reg=ClosureEvidenceRegistry(path); resolver=GovernanceExceptionResolver(path)
    res=resolver.resolve(exception_code="MISSING_AUDIT_EVENT",decision_kind="review_decision",
        artifact_id="REV-1",actor_id="u1",role="reviewer",outcome="CORRECTED_AT_SOURCE",
        reason_code="FIXED",reconciliation_fingerprint=fp)
    eid=res.get("entry_id") or res.get("event_id")
    reg.register(evidence_id="E1",evidence_hash="a"*64,evidence_type="SOURCE_CORRECTION",
        reconciliation_fingerprint=fp,exception_code="MISSING_AUDIT_EVENT",
        decision_kind="review_decision",artifact_id="REV-1",resolution_event_id=eid,
        provenance_ref="OBS-1|REVIEW-1|AUDIT-1",registered_by="u1",verification_state="VERIFIED")
    return reg.list(),resolver.list_resolutions()

def test_integrity_rejects_malformed_or_tampered_shape():
    good={"evidence_id":"E1","evidence_hash":"a"*64,"evidence_type":"SOURCE_CORRECTION",
        "reconciliation_fingerprint":"fp","exception_code":"X","decision_kind":"review",
        "artifact_id":"A","resolution_event_id":"R","provenance_ref":"P",
        "verification_state":"VERIFIED","registered_by":"u","registered_at":"t","policy_version":"phase42-v1"}
    bad=dict(good); bad["evidence_hash"]="not-a-hash"
    assert verify_evidence_integrity([good])["valid"]
    assert not verify_evidence_integrity([bad])["valid"]

def test_attestation_requires_authorized_human_role(tmp_path):
    path=tmp_path/"db.sqlite"; reg=GovernanceAttestationRegistry(path)
    try: reg.attest(actor_id="u1",role="reviewer",reconciliation_fingerprint="r",
        evidence_registry_fingerprint="e",provenance_fingerprint="p",reason="ok")
    except PermissionError: pass
    else: assert False, "reviewer must not attest"

def test_attestation_is_stale_when_evidence_snapshot_changes(tmp_path):
    path=tmp_path/"db.sqlite"; reg=GovernanceAttestationRegistry(path)
    row=reg.attest(actor_id="u1",role="coordinator",reconciliation_fingerprint="r",
        evidence_registry_fingerprint="e1",provenance_fingerprint="p1",reason="Reviewed exact bundle.")
    states=reg.list()
    result=__import__("nema_agora.governance_attestation",fromlist=["evaluate_attestations"]).evaluate_attestations(
        states,reconciliation_fingerprint="r",evidence_registry_fingerprint="e2",
        provenance_fingerprint="p1",integrity_valid=True,provenance_complete=True)
    assert result[0]["effective_state"]=="STALE"

def test_complete_provenance_binds_resolution_and_evidence(tmp_path):
    path=tmp_path/"db.sqlite"; evidence,resolutions=_evidence(path)
    rec=_rec()
    from nema_agora.closure_evidence import evaluate_with_registry
    closure=evaluate_with_registry(rec,resolutions,evidence)
    p=build_provenance_completeness(rec,closure,resolutions,evidence)
    assert p["complete"]
    assert p["items"][0]["fields"]["audit_event"]
    assert p["items"][0]["fields"]["closure_evidence"]

def test_integrity_snapshot_fails_closed_without_verified_evidence(tmp_path):
    path=tmp_path/"db.sqlite"; rec=_rec()
    from nema_agora.closure_evidence import build_operational_report, evaluate_with_registry
    evidence,resolutions=_evidence(path)
    closure=evaluate_with_registry(rec,resolutions,evidence)
    snapshot=build_integrity_snapshot(reconciliation=rec,closure=closure,resolutions=resolutions,
        evidence_rows=evidence,attestations=[])
    assert snapshot["overall_state"]=="PENDING"
    reg=ClosureEvidenceRegistry(path)
    reg.register(evidence_id="E2",evidence_hash="b"*64,evidence_type="SOURCE_CORRECTION",
        reconciliation_fingerprint="fp-1",exception_code="MISSING_AUDIT_EVENT",decision_kind="review_decision",
        artifact_id="REV-1",resolution_event_id=resolutions[0].get("entry_id") or resolutions[0].get("event_id"),
        provenance_ref="OBS-1|REVIEW-1|AUDIT-1",registered_by="u1",verification_state="REGISTERED")
    assert build_integrity_snapshot(reconciliation=rec,closure=closure,resolutions=resolutions,
        evidence_rows=reg.list(),attestations=[])["overall_state"]=="PENDING"

def test_snapshot_attestation_becomes_active_on_exact_snapshot(tmp_path):
    path=tmp_path/"db.sqlite"; evidence,resolutions=_evidence(path); rec=_rec()
    from nema_agora.closure_evidence import evaluate_with_registry
    closure=evaluate_with_registry(rec,resolutions,evidence)
    first=build_integrity_snapshot(reconciliation=rec,closure=closure,resolutions=resolutions,evidence_rows=evidence,attestations=[])
    reg=GovernanceAttestationRegistry(path)
    reg.attest(actor_id="u1",role="coordinator",reconciliation_fingerprint=rec["reconciliation_fingerprint"],
        evidence_registry_fingerprint=first["integrity"]["registry_fingerprint"],
        provenance_fingerprint=first["provenance_fingerprint"],reason="Exact evidence and provenance reviewed.")
    second=build_integrity_snapshot(reconciliation=rec,closure=closure,resolutions=resolutions,
        evidence_rows=evidence,attestations=reg.list())
    assert second["overall_state"]==ATTESTED
    assert second["active_attestation_count"]==1

def test_invalid_provenance_forces_control_required(tmp_path):
    path=tmp_path/"db.sqlite"; rec=_rec()
    snap=build_integrity_snapshot(reconciliation=rec,closure={"results":[]},resolutions=[],evidence_rows=[],attestations=[])
    assert snap["overall_state"]==CONTROL_REQUIRED
