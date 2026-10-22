from nema_agora.research_dossier import build_dossier, validate_dossier

def synthesis():
    return {"claims":[{"claim_id":"C1","claim":"bounded","source_ids":["P1"]}],"limitations":["small"]}

def graph():
    return {"fingerprint":"G1","orphan_claims":[],"missing_parents":[]}

def test_dossier_has_human_review_boundary():
    d=build_dossier(synthesis=synthesis(),graph=graph())
    assert d.review_status=="READY_FOR_HUMAN_REVIEW"
    assert validate_dossier(d)["valid"] is True
    assert d.claim_count==1 and d.linked_claim_count==1

def test_dossier_blocks_unlinked_claims():
    d=build_dossier(synthesis={"claims":[{"claim_id":"C1","source_ids":[]}],"limitations":["small"]},
                    graph={"fingerprint":"G1","orphan_claims":["C1"],"missing_parents":[]})
    assert d.review_status=="CONTROL_REQUIRED"

def test_dossier_rejects_empty_section_content():
    d=build_dossier(synthesis=synthesis(),graph=graph())
    section=d.sections[0]
    from dataclasses import replace
    bad=replace(d,sections=(replace(section,content=""),)+d.sections[1:])
    assert validate_dossier(bad)["valid"] is False
