from nema_agora.evidence_case import EvidenceReference,build_evidence_case,attach_human_review
from nema_agora.reporting import build_case_report

def test_report_is_traceable():
    case=build_evidence_case(case_id="c1",observation={"x":1},evidence=[EvidenceReference("e1","photo","pilot","2026-10-04T12:00:00+00:00","fp")])
    case=attach_human_review(case,reviewer_id="r1",role="coordinator",decision="ACKNOWLEDGED")
    report=build_case_report(case)
    assert report["observation_fingerprint"]==case.observation_fingerprint
    assert report["official_submission"] is False
