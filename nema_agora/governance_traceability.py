"""Phase 37 — end-to-end governance traceability.

Validates explicit links from an originating event through provenance/evidence,
the research report, human publication decision, and governed audit events.
This is an artifact/workflow integrity control; it does not establish
environmental truth, regulatory status, NEMA authorization, or production approval.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import re
from typing import Any, Mapping, Iterable

POLICY_VERSION = "phase37-v1"
CONTROL_REQUIRED = "CONTROL_REQUIRED"
_APPROVED = "APPROVED_FOR_PUBLICATION"
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return dict(value)


def _errors_unique(errors: list[str]) -> list[str]:
    return sorted(set(errors))


def validate_governance_trace(
    *,
    origin_event: Mapping[str, Any],
    provenance_records: Iterable[Mapping[str, Any]],
    graph: Mapping[str, Any] | Any,
    report: Mapping[str, Any],
    publication_decision: Mapping[str, Any] | Any,
    audit_entries: Iterable[Mapping[str, Any]],
    ledger_verification: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail closed unless every required governance reference is explicit."""
    errors: list[str] = []
    records = [dict(r) for r in provenance_records]
    graph_data = _dict(graph)
    decision = _dict(publication_decision)
    report_data = dict(report)
    audit = [dict(e) for e in audit_entries]

    origin_id = str(origin_event.get("event_id", "")).strip()
    origin_type = str(origin_event.get("event_type", "")).strip()
    if not _SAFE_ID.fullmatch(origin_id) or not origin_type:
        errors.append("ORIGIN_EVENT_INVALID")

    provenance_ids = [str(r.get("provenance_id", "")).strip() for r in records]
    event_pairs = [(str(r.get("event_type", "")).strip(), str(r.get("event_id", "")).strip()) for r in records]
    if any(not _SAFE_ID.fullmatch(x) for x in provenance_ids):
        errors.append("PROVENANCE_ID_INVALID_OR_MISSING")
    if len(provenance_ids) != len(set(provenance_ids)):
        errors.append("DUPLICATE_PROVENANCE_ID")
    if len(event_pairs) != len(set(event_pairs)):
        errors.append("DUPLICATE_PROVENANCE_EVENT")

    matching_origin = [r for r in records if str(r.get("event_id", "")).strip() == origin_id]
    if len(matching_origin) != 1:
        errors.append("ORIGIN_EVENT_NOT_UNIQUE_IN_PROVENANCE")
    elif str(matching_origin[0].get("event_type", "")).strip() != origin_type:
        errors.append("ORIGIN_EVENT_TYPE_MISMATCH")

    graph_nodes = graph_data.get("nodes", [])
    graph_node_ids = [str(n.get("node_id", "")).strip() for n in graph_nodes]
    if any(not x for x in graph_node_ids):
        errors.append("GRAPH_NODE_ID_MISSING")
    if len(graph_node_ids) != len(set(graph_node_ids)):
        errors.append("DUPLICATE_GRAPH_NODE_ID")
    node_set = set(graph_node_ids)
    for edge in graph_data.get("edges", []):
        if edge.get("parent_id") not in node_set:
            errors.append("GRAPH_EDGE_PARENT_MISSING")
        if edge.get("child_id") not in node_set:
            errors.append("GRAPH_EDGE_CHILD_MISSING")
    if graph_data.get("orphan_claims") or graph_data.get("missing_parents"):
        errors.append("GRAPH_LINEAGE_INCOMPLETE")

    report_id = str(report_data.get("report_id", "")).strip()
    graph_id = str(graph_data.get("graph_id", "")).strip()
    embedded_graph = report_data.get("provenance_graph", {})
    if not _SAFE_ID.fullmatch(report_id):
        errors.append("REPORT_ID_INVALID_OR_MISSING")
    if embedded_graph.get("graph_id") != graph_id or embedded_graph.get("fingerprint") != graph_data.get("fingerprint"):
        errors.append("REPORT_GRAPH_BINDING_MISMATCH")
    if report_data.get("validation", {}).get("valid") is False:
        errors.append("REPORT_VALIDATION_FAILED")

    claims = list(report_data.get("claim_evidence_limitation_matrix", []))
    claim_ids = [str(c.get("claim_id", "")).strip() for c in claims]
    if any(not x for x in claim_ids):
        errors.append("CLAIM_ID_MISSING")
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("DUPLICATE_CLAIM_ID")
    for claim in claims:
        source_ids = {str(x).strip() for x in claim.get("source_ids", []) if str(x).strip()}
        if not source_ids or not source_ids.intersection(set(provenance_ids)):
            errors.append("CLAIM_SOURCE_UNRESOLVED:" + str(claim.get("claim_id", "")))
        if not claim.get("limitations"):
            errors.append("CLAIM_LIMITATION_MISSING:" + str(claim.get("claim_id", "")))
        claim_node = "CLAIM-" + str(claim.get("claim_id", "")).strip()
        if claim_node and claim_node not in node_set:
            errors.append("CLAIM_GRAPH_NODE_MISSING:" + str(claim.get("claim_id", "")))

    if decision.get("report_id") != report_id:
        errors.append("DECISION_REPORT_BINDING_MISMATCH")
    if decision.get("status") not in {"APPROVED_FOR_PUBLICATION", CONTROL_REQUIRED}:
        errors.append("INVALID_PUBLICATION_DECISION_STATUS")
    gates = decision.get("gates", {})
    blockers = list(decision.get("blockers", []))
    if blockers != sorted(blockers) and set(blockers) != {k for k, v in gates.items() if not v}:
        errors.append("DECISION_BLOCKER_BINDING_MISMATCH")
    if decision.get("status") == _APPROVED and (blockers or not all(bool(v) for v in gates.values())):
        errors.append("APPROVAL_WITH_FAILED_GATES")
    if decision.get("status") == _APPROVED and (not decision.get("reviewer_id") or not str(decision.get("rationale", "")).strip()):
        errors.append("APPROVAL_WITHOUT_HUMAN_SIGNOFF")

    if not ledger_verification.get("valid", False):
        errors.append("AUDIT_LEDGER_INTEGRITY_FAILED")

    publication_events = [
        e for e in audit
        if e.get("event_type") == "GOVERNED_AUDIT_EVENT"
        and isinstance(e.get("payload"), Mapping)
        and e["payload"].get("event_type") == "PUBLICATION_GATE_DECIDED"
        and e["payload"].get("metadata", {}).get("artifact_id") == report_id
    ]
    if len(publication_events) == 0:
        errors.append("PUBLICATION_AUDIT_EVENT_MISSING")
    elif len(publication_events) > 1:
        errors.append("PUBLICATION_AUDIT_EVENT_AMBIGUOUS")
    else:
        meta = publication_events[0]["payload"].get("metadata", {})
        expected_status = decision.get("status")
        if meta.get("status") != expected_status:
            errors.append("PUBLICATION_AUDIT_STATUS_MISMATCH")
        expected_decision = "APPROVE" if expected_status == _APPROVED else "HUMAN_REVIEW_REQUIRED"
        if meta.get("decision") != expected_decision:
            errors.append("PUBLICATION_AUDIT_DECISION_MISMATCH")

    origin_audit_events = [
        e for e in audit
        if e.get("event_type") == "GOVERNED_AUDIT_EVENT"
        and isinstance(e.get("payload"), Mapping)
        and e["payload"].get("event_id") == origin_id
    ]
    origin_audit_coverage = len(origin_audit_events) == 1
    # Phase 36 does not instrument every workflow yet. We report missing origin
    # coverage separately rather than pretending it is automatically captured.
    warnings = [] if origin_audit_coverage else ["ORIGIN_AUDIT_EVENT_NOT_INSTRUMENTED"]

    trace_material = {
        "origin_event": {"event_id": origin_id, "event_type": origin_type},
        "report_id": report_id,
        "graph_id": graph_id,
        "claim_ids": sorted(claim_ids),
        "publication_decision_id": decision.get("decision_id"),
        "publication_audit_entry_id": publication_events[0].get("entry_id") if len(publication_events) == 1 else None,
    }
    trace_fingerprint = _fingerprint(trace_material)
    valid = not errors
    return {
        "valid": valid,
        "status": "TRACEABLE" if valid else CONTROL_REQUIRED,
        "errors": _errors_unique(errors),
        "warnings": sorted(set(warnings)),
        "origin_event_id": origin_id,
        "origin_event_type": origin_type,
        "report_id": report_id,
        "graph_id": graph_id,
        "publication_decision_id": decision.get("decision_id"),
        "publication_audit_entry_id": publication_events[0].get("entry_id") if len(publication_events) == 1 else None,
        "origin_audit_coverage": origin_audit_coverage,
        "trace_fingerprint": trace_fingerprint,
        "policy_version": POLICY_VERSION,
        "decision_notice": (
            "Traceability is an artifact/workflow integrity control. It does not establish "
            "environmental truth, environmental impact, regulatory status, NEMA authorization, "
            "production approval, enforcement authority, emergency-response authority, or autonomous decision authority."
        ),
    }


def serialise_trace(result: Mapping[str, Any]) -> str:
    return json.dumps(dict(result), sort_keys=True, indent=2, ensure_ascii=False)
