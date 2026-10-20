"""Phase 26 — controlled pilot readiness governance.

This module combines engineering evidence into a conservative readiness gate.
A positive result only means the prototype has sufficient evidence for a
human-supervised controlled pilot review. It is not NEMA approval, regulatory
authorization, environmental truth, production approval, enforcement
authority, or emergency-response authorization.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
import hashlib
import json

POLICY_VERSION = "phase26-v1"
READY = "READY_FOR_CONTROLLED_PILOT_REVIEW"
NOT_READY = "NOT_READY"

@dataclass(frozen=True)
class PilotReadinessPolicy:
    minimum_evidence_per_domain: int = 10
    minimum_shadow_runs: int = 10
    maximum_shadow_error_rate: float = 0.05
    require_reproducibility_manifest: bool = True
    require_human_governance: bool = True

@dataclass(frozen=True)
class PilotReadiness:
    readiness_id: str
    decision: str
    policy_version: str
    gates: dict[str, bool]
    evidence: dict[str, Any]
    warnings: tuple[str, ...]
    created_at: str
    decision_notice: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def evaluate_pilot_readiness(
    *,
    evidence_scorecard: Mapping[str, Any],
    shadow_monitoring: Mapping[str, Any],
    reproducibility_manifest: Mapping[str, Any] | None,
    human_governance: Mapping[str, Any],
    policy: PilotReadinessPolicy | None = None,
) -> PilotReadiness:
    """Evaluate a fail-closed, human-governed controlled-pilot gate."""
    policy = policy or PilotReadinessPolicy()
    domains = evidence_scorecard.get("domains", {})
    domain_counts = {
        str(name): max(0, int(value.get("count", 0)))
        for name, value in domains.items()
        if isinstance(value, Mapping)
    }
    evidence_gate = bool(domain_counts) and all(
        count >= policy.minimum_evidence_per_domain
        for count in domain_counts.values()
    )
    total_runs = max(0, int(shadow_monitoring.get("total_runs", 0)))
    error_rate = float(shadow_monitoring.get("error_rate", 1.0))
    shadow_gate = (
        total_runs >= policy.minimum_shadow_runs
        and error_rate <= policy.maximum_shadow_error_rate
        and shadow_monitoring.get("status") == "HEALTHY_WITHIN_SHADOW_POLICY"
    )
    manifest_gate = (
        not policy.require_reproducibility_manifest
        or (
            isinstance(reproducibility_manifest, Mapping)
            and bool(reproducibility_manifest.get("manifest_id"))
            and bool(reproducibility_manifest.get("git_revision"))
        )
    )
    governance_gate = (
        not policy.require_human_governance
        or (
            human_governance.get("human_review_required") is True
            and human_governance.get("explicit_lifecycle_control") is True
            and human_governance.get("autonomous_state_change_blocked") is True
        )
    )
    gates = {
        "evidence_domains_sufficient": evidence_gate,
        "shadow_operations_within_policy": shadow_gate,
        "reproducibility_manifest_present": manifest_gate,
        "human_governance_controls_present": governance_gate,
    }
    warnings: list[str] = []
    if not evidence_gate:
        warnings.append("EVIDENCE_COVERAGE_INSUFFICIENT")
    if not shadow_gate:
        warnings.append("SHADOW_OPERATIONS_NOT_WITHIN_POLICY")
    if not manifest_gate:
        warnings.append("REPRODUCIBILITY_MANIFEST_MISSING_OR_INCOMPLETE")
    if not governance_gate:
        warnings.append("HUMAN_GOVERNANCE_CONTROLS_INCOMPLETE")
    decision = READY if all(gates.values()) else NOT_READY
    evidence = {
        "domain_counts": domain_counts,
        "shadow_runs": total_runs,
        "shadow_error_rate": error_rate,
        "shadow_status": shadow_monitoring.get("status"),
        "manifest_id": (
            reproducibility_manifest.get("manifest_id")
            if isinstance(reproducibility_manifest, Mapping) else None
        ),
        "human_governance": dict(human_governance),
    }
    readiness_id = _fingerprint({
        "decision": decision,
        "policy_version": POLICY_VERSION,
        "gates": gates,
        "evidence": evidence,
    })
    return PilotReadiness(
        readiness_id=readiness_id,
        decision=decision,
        policy_version=POLICY_VERSION,
        gates=gates,
        evidence=evidence,
        warnings=tuple(warnings),
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        decision_notice=(
            "This gate evaluates engineering/research readiness for a "
            "human-supervised controlled pilot review only. It does not "
            "establish environmental truth, environmental impact, regulatory "
            "status, NEMA authorization, production approval, enforcement "
            "authority, or emergency response capability."
        ),
    )

def serialise_readiness(result: PilotReadiness) -> str:
    return json.dumps(result.to_dict(), sort_keys=True, indent=2)
