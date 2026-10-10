import json
import sqlite3
from dataclasses import replace

from nema_agora.audit_events import AuditEventCapture
from nema_agora.audit_ledger import AuditLedger
from nema_agora.evidence_graph import build_evidence_graph, build_research_report
from nema_agora.evidence_synthesis import build_evidence_synthesis
from nema_agora.governance_traceability import CONTROL_REQUIRED, validate_governance_trace


def _bundle(tmp_path):
    db = tmp_path / "audit.sqlite"
    ledger = AuditLedger(db)
    records = [{
        "provenance_id": "PROV-1",
        "event_type": "EVALUATION",
        "event_id": "origin-1",
        "dataset_version": "demo-v1",
        "dataset_hash": "a" * 64,
        "model_identity": {"adapter": "local"},
        "evidence_hash": "b" * 64,
        "parent_ids": [],
    }]
    synthesis = build_evidence_synthesis(
        evidence_domains={
            "ENGINEERING": {"count": 1, "source_ids": ["PROV-1"], "limitations": ["bounded"]},
            "WORKFLOW_OUTCOMES": {"count": 1, "source_ids": ["PROV-1"], "limitations": ["bounded"]},
            "HUMAN_GOVERNANCE": {"count": 1, "source_ids": ["PROV-1"], "limitations": ["bounded"]},
            "REPRODUCIBILITY": {"count": 1, "source_ids": ["PROV-1"], "limitations": ["bounded"]},
            "ACCESSIBILITY": {"count": 1, "source_ids": ["PROV-1"], "limitations": ["bounded"]},
            "FIELD_EVALUATION": {"count": 1, "source_ids": ["PROV-1"], "limitations": ["bounded"]},
        },
        global_limitations=["bounded"],
    )
    graph = build_evidence_graph(provenance_records=records, synthesis=synthesis.to_dict())
    report = build_research_report(synthesis=synthesis.to_dict(), graph=graph)
    decision = {
        "decision_id": "PUB-1", "report_id": report["report_id"],
        "status": "APPROVED_FOR_PUBLICATION",
        "gates": {"one": True}, "blockers": [], "reviewer_id": "reviewer-1",
        "rationale": "Human reviewed.", "evidence_fingerprint": "x",
    }
    event = AuditEventCapture(ledger).record(
        event_id="publication-1", event_type="PUBLICATION_GATE_DECIDED", actor_id="reviewer-1",
        payload={"artifact_id": report["report_id"], "status": decision["status"], "decision": "APPROVE",
                 "reason_code": "POLICY_GATE", "source_module": "publication_control",
                 "recorded_by_role": "reviewer", "policy_version": "phase36-v1"},
    )
    return db, records, graph, report, decision, [event["entry"]], ledger.verify()


def test_trace_success(tmp_path):
    db, records, graph, report, decision, audit, verification = _bundle(tmp_path)
    result = validate_governance_trace(
        origin_event={"event_id": "origin-1", "event_type": "EVALUATION"},
        provenance_records=records, graph=graph, report=report,
        publication_decision=decision, audit_entries=audit,
        ledger_verification=verification,
    )
    assert result["valid"] is True
    assert result["status"] == "TRACEABLE"
    assert result["origin_audit_coverage"] is False
    assert result["warnings"] == ["ORIGIN_AUDIT_EVENT_NOT_INSTRUMENTED"]


def test_missing_publication_audit_event_fails_closed(tmp_path):
    _, records, graph, report, decision, _, verification = _bundle(tmp_path)
    result = validate_governance_trace(
        origin_event={"event_id": "origin-1", "event_type": "EVALUATION"},
        provenance_records=records, graph=graph, report=report,
        publication_decision=decision, audit_entries=[],
        ledger_verification=verification,
    )
    assert result["valid"] is False
    assert result["status"] == CONTROL_REQUIRED
    assert "PUBLICATION_AUDIT_EVENT_MISSING" in result["errors"]


def test_broken_report_graph_binding_fails(tmp_path):
    _, records, graph, report, decision, audit, verification = _bundle(tmp_path)
    broken = dict(report)
    broken["provenance_graph"] = dict(report["provenance_graph"])
    broken["provenance_graph"]["fingerprint"] = "f" * 64
    result = validate_governance_trace(
        origin_event={"event_id": "origin-1", "event_type": "EVALUATION"},
        provenance_records=records, graph=graph, report=broken,
        publication_decision=decision, audit_entries=audit,
        ledger_verification=verification,
    )
    assert result["valid"] is False
    assert "REPORT_GRAPH_BINDING_MISMATCH" in result["errors"]


def test_duplicate_provenance_id_fails(tmp_path):
    _, records, graph, report, decision, audit, verification = _bundle(tmp_path)
    duplicate = records + [dict(records[0])]
    result = validate_governance_trace(
        origin_event={"event_id": "origin-1", "event_type": "EVALUATION"},
        provenance_records=duplicate, graph=graph, report=report,
        publication_decision=decision, audit_entries=audit,
        ledger_verification=verification,
    )
    assert result["valid"] is False
    assert "DUPLICATE_PROVENANCE_ID" in result["errors"]


def test_tampered_ledger_fails_closed(tmp_path):
    _, records, graph, report, decision, audit, verification = _bundle(tmp_path)
    assert verification["valid"] is True
    verification["valid"] = False
    verification["errors"] = ["ENTRY_HASH_MISMATCH:1"]
    result = validate_governance_trace(
        origin_event={"event_id": "origin-1", "event_type": "EVALUATION"},
        provenance_records=records, graph=graph, report=report,
        publication_decision=decision, audit_entries=audit,
        ledger_verification=verification,
    )
    assert result["valid"] is False
    assert "AUDIT_LEDGER_INTEGRITY_FAILED" in result["errors"]
