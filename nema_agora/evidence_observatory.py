"""Phase 46 — governance evidence observatory.

Read-only aggregation of Phase 43–45 governance evidence. This module never
creates, changes or infers a governance decision.
"""
from __future__ import annotations
from typing import Any, Iterable, Mapping

POLICY_VERSION = "phase46-v1"

def build_observatory(*, attestations: Iterable[Mapping[str, Any]], lifecycle_items: Iterable[Mapping[str, Any]],
                      provenance_result: Mapping[str, Any], integrity_valid: bool,
                      provenance_complete: bool) -> dict[str, Any]:
    atts=list(attestations); items=list(lifecycle_items)
    attested=sum(str(x.get("effective_state",""))=="ATTESTED" for x in atts)
    active=sum(str(x.get("lifecycle_state",""))=="ACTIVE" for x in items)
    stale=sum(str(x.get("lifecycle_state",""))=="STALE" for x in items)
    control=sum(str(x.get("lifecycle_state",""))=="CONTROL_REQUIRED" for x in items)
    failures=len(provenance_result.get("failures",[]))
    gaps=[]
    if not integrity_valid: gaps.append("INTEGRITY_FAILED")
    if not provenance_complete: gaps.append("PROVENANCE_INCOMPLETE")
    if not atts: gaps.append("NO_ATTESTATIONS")
    if not provenance_result.get("bindings"): gaps.append("NO_PROVENANCE_BINDINGS")
    if failures: gaps.append("PROVENANCE_FAILURES")
    overall="CONTROL_REQUIRED" if (not integrity_valid or not provenance_complete or control or failures) else ("READY_FOR_HUMAN_REVIEW" if gaps else "EVIDENCE_COVERAGE_OK")
    return {"policy_version":POLICY_VERSION,"overall_state":overall,
            "coverage":{"attestations":len(atts),"attested":attested,"lifecycle_items":len(items),
                        "active":active,"stale":stale,"control_required":control,
                        "provenance_bindings":len(provenance_result.get("bindings",[])),
                        "provenance_valid":provenance_result.get("valid_count",0),"provenance_failures":failures},
            "gaps":sorted(set(gaps)),
            "notice":"Read-only engineering/research evidence. No metric or state here establishes environmental truth, NEMA authorization, regulatory status, production approval, enforcement, emergency response or autonomous authority."}
