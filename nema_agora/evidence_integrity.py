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


# Local file verification extension. Kept separate from the phase-33 artifact graph
# audit above because byte-level evidence verification needs an actual local root.
from pathlib import Path
import re

class EvidenceIntegrityError(ValueError):
    """Raised when local evidence manifest or asset checks fail."""

_EVIDENCE_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
_EVIDENCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
DEFAULT_EVIDENCE_MAX_BYTES = 100 * 1024 * 1024


def verify_evidence_assets(*, root_directory: str | Path,
                           evidence_assets: Iterable[Mapping[str, Any]],
                           max_asset_bytes: int = DEFAULT_EVIDENCE_MAX_BYTES) -> dict[str, Any]:
    """Hash actual local evidence files and compare them with declared SHA-256.

    Rejects path traversal, absolute paths, symlink components, duplicate IDs
    and paths, missing/non-regular files and files above the configured limit.
    No remote URLs are fetched. A matching digest does not authenticate source.
    """
    if not isinstance(evidence_assets, Iterable) or isinstance(evidence_assets, (str, bytes, Mapping)):
        raise EvidenceIntegrityError("evidence_assets must be a non-empty array.")
    assets = list(evidence_assets)
    if not assets:
        raise EvidenceIntegrityError("evidence_assets must be a non-empty array.")
    if isinstance(max_asset_bytes, bool) or not isinstance(max_asset_bytes, int) or max_asset_bytes <= 0:
        raise EvidenceIntegrityError("max_asset_bytes must be a positive integer.")
    try:
        root = Path(root_directory).expanduser().resolve(strict=True)
    except (OSError, TypeError) as exc:
        raise EvidenceIntegrityError("root_directory must be an existing directory.") from exc
    if not root.is_dir():
        raise EvidenceIntegrityError("root_directory must be an existing directory.")
    seen_ids, seen_paths, results = set(), set(), []
    total_bytes = 0
    for index, item in enumerate(assets):
        if not isinstance(item, Mapping):
            raise EvidenceIntegrityError(f"evidence_assets[{index}] must be an object.")
        evidence_id = item.get("evidence_id")
        relative_path = item.get("relative_path")
        expected = item.get("sha256")
        if not isinstance(evidence_id, str) or not _EVIDENCE_ID_PATTERN.fullmatch(evidence_id.strip()):
            raise EvidenceIntegrityError(f"evidence_assets[{index}].evidence_id is invalid.")
        evidence_id = evidence_id.strip()
        if evidence_id in seen_ids:
            raise EvidenceIntegrityError(f"duplicate evidence_id: {evidence_id}.")
        seen_ids.add(evidence_id)
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise EvidenceIntegrityError(f"evidence_assets[{index}].relative_path is required.")
        rel = Path(relative_path)
        if rel.is_absolute() or ".." in rel.parts or "\\\\" in relative_path or relative_path.strip() in {".", "./"}:
            raise EvidenceIntegrityError(f"unsafe relative_path for evidence {evidence_id}.")
        normalized = rel.as_posix()
        if normalized in seen_paths:
            raise EvidenceIntegrityError(f"duplicate evidence path: {normalized}.")
        seen_paths.add(normalized)
        if not isinstance(expected, str) or not _EVIDENCE_SHA256.fullmatch(expected):
            raise EvidenceIntegrityError(f"evidence_assets[{index}].sha256 must be a 64-character hex digest.")
        candidate = root
        for part in rel.parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise EvidenceIntegrityError(f"symlink path component rejected for evidence {evidence_id}.")
        try:
            resolved = candidate.resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            raise EvidenceIntegrityError(f"evidence file missing or inaccessible: {evidence_id}.") from exc
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise EvidenceIntegrityError(f"evidence path escapes root or is not a regular file: {evidence_id}.")
        if resolved.stat().st_size > max_asset_bytes:
            raise EvidenceIntegrityError(f"evidence file exceeds size limit: {evidence_id}.")
        digest, byte_count = hashlib.sha256(), 0
        with resolved.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                byte_count += len(chunk)
                if byte_count > max_asset_bytes:
                    raise EvidenceIntegrityError(f"evidence file grew beyond size limit: {evidence_id}.")
                digest.update(chunk)
        actual = digest.hexdigest()
        matches = actual.lower() == expected.lower()
        total_bytes += byte_count
        results.append({"evidence_id": evidence_id, "relative_path": normalized,
                        "size_bytes": byte_count, "expected_sha256": expected.lower(),
                        "actual_sha256": actual, "matches": matches,
                        "state": "HASH_MATCH" if matches else "HASH_MISMATCH"})
    all_match = all(item["matches"] for item in results)
    return {"schema_version": "nema-evidence-integrity-v1",
            "state": "LOCAL_BYTES_MATCH_DECLARED_HASHES_NOT_AUTHENTICATED" if all_match else "BLOCKED_EVIDENCE_HASH_MISMATCH",
            "decision": "HASHES_MATCH" if all_match else "BLOCK_EVIDENCE_USE",
            "asset_count": len(results), "total_bytes_hashed": total_bytes, "assets": results,
            "limitations": [
                "A matching digest proves only that inspected bytes match the supplied digest; it does not authenticate creator, capture time, provenance, or truth.",
                "The expected digest must come from a trusted independently recorded source to provide meaningful tamper evidence.",
                "Only local files under the selected root are read; remote URLs are never fetched and scientific validity is not inferred."
            ]}
