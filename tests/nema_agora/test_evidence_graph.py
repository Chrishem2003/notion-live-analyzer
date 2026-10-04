from nema_agora.evidence_graph import build_evidence_graph, build_research_report, validate_graph

def prov(pid,parent=()):
    return {"provenance_id":pid,"event_type":"EVALUATION_RUN","event_id":pid,"dataset_version":"D1","dataset_hash":"H1","model_identity":{},"parent_ids":list(parent),"evidence_hash":"E1"}

def syn():
    return {"evidence_fingerprint":"SYN1","domains":{"ENGINEERING":{"count":1}},"limitations":["small"],"claims":[{"claim_id":"C1","claim":"Test claim","evidence_domain":"ENGINEERING","evidence_type":"TEST","source_ids":["P2"],"sample_size":1,"limitations":["small"],"support_status":"SUPPORTED_WITH_LIMITATIONS"}]}

def test_graph_links_parent_and_claim():
    g=build_evidence_graph(provenance_records=[prov("P1"),prov("P2",("P1",))],synthesis=syn())
    assert validate_graph(g)["valid"] is True
    assert len(g.nodes)==3 and len(g.edges)==2

def test_graph_fails_closed_on_missing_parent():
    g=build_evidence_graph(provenance_records=[prov("P2",("MISSING",))],synthesis={"claims":[]})
    assert validate_graph(g)["valid"] is False

def test_graph_marks_unlinked_claim():
    g=build_evidence_graph(provenance_records=[prov("P1")],synthesis={"domains":{},"claims":[{"claim_id":"C1","claim":"x","evidence_domain":"ENGINEERING","source_ids":["NOPE"],"sample_size":1,"limitations":["x"]}]})
    assert "C1" in g.orphan_claims and validate_graph(g)["valid"] is False

def test_report_identity_is_reproducible():
    records=[prov("P1"),prov("P2",("P1",))]
    a=build_evidence_graph(provenance_records=records,synthesis=syn())
    b=build_evidence_graph(provenance_records=records,synthesis=syn())
    assert a.fingerprint==b.fingerprint
    assert build_research_report(synthesis=syn(),graph=a)["report_id"]==build_research_report(synthesis=syn(),graph=b)["report_id"]
