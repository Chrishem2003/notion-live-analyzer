"""Phase 33 — evidence integrity and audit hardening.

Verifies canonical content fingerprints, identifier uniqueness, graph lineage and
publication evidence bindings. These checks establish artifact integrity only.
"""
from __future__ import annotations
from typing import Any, Iterable, Mapping
import hashlib, json

POLICY_VERSION="phase33-v1"

def canonical_fingerprint(value:Any)->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def audit_evidence_integrity(*, provenance_records:Iterable[Mapping[str,Any]],
                             graph:Mapping[str,Any]|Any,
                             report:Mapping[str,Any],
                             publication_decision:Mapping[str,Any]|Any|None=None)->dict[str,Any]:
    records=list(provenance_records)
    errors=[]; warnings=[]
    ids=[str(r.get("provenance_id","")).strip() for r in records]
    if any(not x for x in ids): errors.append("PROVENANCE_ID_MISSING")
    if len(ids)!=len(set(ids)): errors.append("DUPLICATE_PROVENANCE_ID")
    events=[(str(r.get("event_type","")),str(r.get("event_id",""))) for r in records]
    if len(events)!=len(set(events)): errors.append("DUPLICATE_EVENT_IDENTITY")
    known=set(ids)
    missing=sorted({str(p) for r in records for p in r.get("parent_ids",()) if str(p) not in known})
    if missing: errors.append("MISSING_PROVENANCE_PARENT")
    graph_data=graph.to_dict() if hasattr(graph,"to_dict") else dict(graph)
    nodes=graph_data.get("nodes",[])
    node_ids=[str(n.get("node_id","")) for n in nodes]
    if len(node_ids)!=len(set(node_ids)): errors.append("DUPLICATE_GRAPH_NODE_ID")
    node_set=set(node_ids)
    for edge in graph_data.get("edges",[]):
        if edge.get("parent_id") not in node_set: errors.append("GRAPH_EDGE_PARENT_MISSING")
        if edge.get("child_id") not in node_set: errors.append("GRAPH_EDGE_CHILD_MISSING")
    graph_payload={"nodes":nodes,"edges":graph_data.get("edges",[]),
        "orphan_claims":graph_data.get("orphan_claims",[]),
        "missing_parents":graph_data.get("missing_parents",[])}
    computed_graph_fp=canonical_fingerprint(graph_payload)
    supplied_graph_fp=graph_data.get("fingerprint")
    graph_fp_valid=supplied_graph_fp==computed_graph_fp
    if not graph_fp_valid: errors.append("GRAPH_FINGERPRINT_MISMATCH")
    expected_graph_id="GRAPH-"+computed_graph_fp[:16].upper()
    if graph_data.get("graph_id")!=expected_graph_id: errors.append("GRAPH_ID_MISMATCH")
    report_data=dict(report)
    embedded=report_data.get("provenance_graph",{})
    if embedded and embedded.get("fingerprint")!=supplied_graph_fp:
        errors.append("REPORT_GRAPH_BINDING_MISMATCH")
    claims=report_data.get("claim_evidence_limitation_matrix",[])
    claim_ids=[str(c.get("claim_id","")).strip() for c in claims]
    if any(not c for c in claim_ids): errors.append("CLAIM_ID_MISSING")
    if len(claim_ids)!=len(set(claim_ids)): errors.append("DUPLICATE_CLAIM_ID")
    for claim in claims:
        if not claim.get("limitations"): warnings.append("CLAIM_LIMITATION_MISSING:"+str(claim.get("claim_id","")))
        sources={str(s) for s in claim.get("source_ids",[]) if str(s).strip()}
        if not sources.intersection(known): errors.append("CLAIM_SOURCE_UNRESOLVED:"+str(claim.get("claim_id","")))
    report_payload={k:v for k,v in report_data.items() if k not in ("integrity_audit","integrity_fingerprint")}
    report_fp=canonical_fingerprint(report_payload)
    decision_data=publication_decision.to_dict() if hasattr(publication_decision,"to_dict") else dict(publication_decision or {})
    if decision_data:
        if decision_data.get("report_id")!=report_data.get("report_id"): errors.append("DECISION_REPORT_BINDING_MISMATCH")
        gates=decision_data.get("gates",{})
        blockers=decision_data.get("blockers",[])
        if decision_data.get("status")=="APPROVED_FOR_PUBLICATION" and (blockers or not gates or not all(gates.values())):
            errors.append("APPROVAL_WITH_FAILED_GATES")
    return {"valid":not errors,"errors":sorted(set(errors)),"warnings":sorted(set(warnings)),
        "provenance_records":len(records),"graph_nodes":len(nodes),"graph_edges":len(graph_data.get("edges",[])),
        "claims":len(claims),"graph_fingerprint_valid":graph_fp_valid,
        "computed_graph_fingerprint":computed_graph_fp,"report_fingerprint":report_fp,
        "publication_decision_present":bool(decision_data),"policy_version":POLICY_VERSION,
        "decision_notice":"Artifact integrity only; not environmental truth/impact, NEMA authorization, regulatory status, or production approval."}
