from nema_agora.case_pipeline import assemble_case, review_case, export_case
from nema_agora.evidence_case import EvidenceReference

def test_pipeline_requires_review_before_export():
    ref=EvidenceReference("e1","photo","pilot","2026-10-04T12:00:00+00:00","fp")
    result=assemble_case(case_id="c1",observation={"x":1},evidence=[ref])
    assert result.validation["valid"]
    try: export_case(result)
    except ValueError: pass
    else: raise AssertionError("export must require human review")
    result=review_case(result,reviewer_id="r1",role="coordinator",decision="ACKNOWLEDGED")
    result=export_case(result)
    assert result.case.state=="EXPORTED"
    assert result.validation["execution_gate"]=="CLOSED"
