from nema_agora.evidence_case import EvidenceReference,build_evidence_case,attach_human_review,mark_exported
from nema_agora.evidence_export import build_export_package
def test_export_package_is_non_submission():
    c=build_evidence_case(case_id="c1",observation={"x":1},
      evidence=[EvidenceReference("e1","photo","pilot","2026-10-04T12:00:00+00:00","fp")])
    c=mark_exported(attach_human_review(c,reviewer_id="r1",role="coordinator",decision="ACKNOWLEDGED"))
    p=build_export_package(c)
    assert p["official_submission"] is False
    assert p["execution_gate"]=="CLOSED"
