from nema_agora.evidence_synthesis import EvidenceClaim, build_evidence_synthesis, validate_synthesis

def _domains():
    return {
        "ENGINEERING":{"count":20,"source_ids":["CI-1"],"sample_size":20,"metrics":{"tests":20}},
        "WORKFLOW_OUTCOMES":{"count":12,"source_ids":["OS-1"],"sample_size":12},
        "HUMAN_GOVERNANCE":{"count":15,"source_ids":["REV-1"],"sample_size":15},
        "REPRODUCIBILITY":{"count":10,"source_ids":["MAN-1"],"sample_size":10},
        "ACCESSIBILITY":{"count":11,"source_ids":["AX-1"],"sample_size":11},
        "FIELD_EVALUATION":{"count":6,"source_ids":["FE-1"],"sample_size":6},
    }

def test_synthesis_builds_claim_evidence_limitation_matrix():
    result=build_evidence_synthesis(evidence_domains=_domains())
    assert result.synthesis_id.startswith("SYN-")
    assert len(result.claims)==6
    assert all(claim.source_ids for claim in result.claims)
    assert all(claim.limitations for claim in result.claims)
    assert validate_synthesis(result)["valid"] is True

def test_synthesis_fingerprint_is_reproducible():
    first=build_evidence_synthesis(evidence_domains=_domains())
    second=build_evidence_synthesis(evidence_domains=_domains())
    assert first.evidence_fingerprint==second.evidence_fingerprint
    assert first.synthesis_id==second.synthesis_id

def test_missing_source_marks_claim_evidence_thin():
    domains=_domains()
    domains["ACCESSIBILITY"]={"count":10,"sample_size":10,"source_ids":[]}
    result=build_evidence_synthesis(evidence_domains=domains)
    claim=next(c for c in result.claims if c.evidence_domain=="ACCESSIBILITY")
    assert claim.support_status=="EVIDENCE_THIN"

def test_custom_claim_requires_limitation_and_valid_domain():
    claim=EvidenceClaim("C-X","A bounded claim","ENGINEERING","TEST",("S1",),20,("Limited sample.",))
    result=build_evidence_synthesis(evidence_domains=_domains(),claims=[claim])
    assert validate_synthesis(result)["valid"] is True

def test_unknown_domain_fails_closed():
    try:
        build_evidence_synthesis(evidence_domains={"UNKNOWN":{"count":1}})
    except ValueError as exc:
        assert "Unsupported evidence domain" in str(exc)
    else:
        raise AssertionError("unknown domain must fail")
