from nema_agora.evidence_case import *
def make_case():
    ref=EvidenceReference("img-1","image","pilot-upload","2026-10-04T12:00:00+00:00","abc123")
    finding=AdvisoryFinding("finding-1","pilot-model","1","Advisory observation requiring human review",0.72,("abc123",),"2026-10-04T12:01:00+00:00")
    return build_evidence_case(case_id="case-001",observation={"site_ref":"pilot-site","measurement":42},
                               evidence=[ref],findings=[finding],created_at="2026-10-04T12:02:00+00:00")
def test_build_is_reviewable_and_provenance_bound():
    case=make_case(); assert case.state=="READY_FOR_REVIEW"; assert len(case.provenance_fingerprint)==64
    assert validate_evidence_case(case)["valid"] is True
def test_review_then_export_requires_human_decision():
    reviewed=attach_human_review(make_case(),reviewer_id="reviewer-1",role="coordinator",decision="ACKNOWLEDGED")
    assert mark_exported(reviewed).state=="EXPORTED"
def test_export_without_review_is_blocked():
    try: mark_exported(make_case())
    except ValueError as exc: assert "human-reviewed" in str(exc)
    else: raise AssertionError("expected export gate")
def test_non_advisory_finding_is_rejected():
    f=AdvisoryFinding("f","m","1","x",0.5,(),"2026-10-04T12:00:00+00:00",False)
    try: build_evidence_case(case_id="case-002",observation={"x":1},evidence=[],findings=[f])
    except ValueError as exc: assert "advisory_only" in str(exc)
    else: raise AssertionError("expected advisory-only gate")
