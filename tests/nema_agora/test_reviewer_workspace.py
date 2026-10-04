from nema_agora.evidence_case import EvidenceReference, build_evidence_case
from nema_agora.evidence_case_store import EvidenceCaseStore
from nema_agora.reviewer_workspace import ReviewerWorkspace

def test_reviewer_workspace_exposes_gate(tmp_path):
    store=EvidenceCaseStore(tmp_path/"cases.db")
    case=build_evidence_case(case_id="c1",observation={"x":1},
        evidence=[EvidenceReference("e1","photo","pilot","2026-10-04T12:00:00+00:00","fp")],
        created_at="2026-10-04T12:01:00+00:00")
    store.append(case)
    ws=ReviewerWorkspace(store)
    view=ws.inspect("c1")
    assert view["review_required"] is True
    assert view["execution_gate"]=="CLOSED"
    reviewed=ws.review(case,reviewer_id="r1",role="coordinator",decision="ACKNOWLEDGED")
    assert ws.validate(reviewed)["valid"] is True
