from dataclasses import replace
from nema_agora.evidence_graph import build_evidence_graph, build_research_report
from nema_agora.evidence_integrity import audit_evidence_integrity, canonical_fingerprint

def _prov(pid="P1",event="E1",parents=()):
    return {"provenance_id":pid,"event_type":"EVALUATION_RUN","event_id":event,"parent_ids":list(parents),
            "dataset_version":"D1","dataset_hash":"DH","model_identity":{},"evidence_hash":"EH"}

def _artifacts(records=None):
    records=records or [_prov()]
    syn={"evidence_fingerprint":"S1","domains":{},"limitations":["bounded"],"claims":[
        {"claim_id":"C1","claim":"bounded claim","source_ids":["P1"],"sample_size":1,"limitations":["small"],"evidence_domain":"ENGINEERING"}]}
    graph=build_evidence_graph(provenance_records=records,synthesis=syn)
    report=build_research_report(synthesis=syn,graph=graph)
    return records,graph,report

def test_integrity_accepts_consistent_artifacts():
    records,graph,report=_artifacts()
    result=audit_evidence_integrity(provenance_records=records,graph=graph,report=report)
    assert result["valid"] is True
    assert result["graph_fingerprint_valid"] is True

def test_integrity_detects_duplicate_provenance_ids():
    records,graph,report=_artifacts()
    result=audit_evidence_integrity(provenance_records=records+[dict(records[0])],graph=graph,report=report)
    assert "DUPLICATE_PROVENANCE_ID" in result["errors"]

def test_integrity_detects_tampered_graph_fingerprint():
    records,graph,report=_artifacts()
    bad=replace(graph,fingerprint="tampered")
    result=audit_evidence_integrity(provenance_records=records,graph=bad,report=report)
    assert "GRAPH_FINGERPRINT_MISMATCH" in result["errors"]

def test_integrity_detects_duplicate_event_identity():
    records,graph,report=_artifacts([_prov("P1","SAME"),_prov("P2","SAME")])
    result=audit_evidence_integrity(provenance_records=records,graph=graph,report=report)
    assert "DUPLICATE_EVENT_IDENTITY" in result["errors"]

def test_integrity_detects_report_graph_mismatch():
    records,graph,report=_artifacts()
    report["provenance_graph"]["fingerprint"]="wrong"
    result=audit_evidence_integrity(provenance_records=records,graph=graph,report=report)
    assert "REPORT_GRAPH_BINDING_MISMATCH" in result["errors"]
