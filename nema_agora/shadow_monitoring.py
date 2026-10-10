"""Phase 18 shadow monitoring and evidence observatory.

This module measures operational evidence from the Phase 17 controlled-shadow
ledger. It does not infer environmental truth, regulatory status, model
accuracy, or production suitability from unlabeled shadow traffic.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import math

from nema_agora.evaluation import validate_advisory_output

POLICY_VERSION = "phase18-v1"

@dataclass(frozen=True)
class ShadowMonitoringPolicy:
    minimum_runs_for_stability: int = 10
    maximum_error_rate: float = 0.05
    maximum_p95_latency_ms: float = 5000.0

@dataclass(frozen=True)
class ShadowMonitoringSnapshot:
    admission_id: str | None
    provider: str | None
    model_version: str | None
    adapter_name: str | None
    policy_version: str
    total_runs: int
    successful_runs: int
    error_runs: int
    unique_cases: int
    error_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    human_review_contract_violations: int
    identity_consistency_violations: int
    safety_contract_violations: int
    status: str
    alerts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["alerts"] = list(self.alerts)
        return result

def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile / 100.0 * len(ordered)))
    return float(ordered[rank - 1])

def build_shadow_monitoring_snapshot(
    runs: list[dict[str, Any]],
    *,
    admission_id: str | None = None,
    policy: ShadowMonitoringPolicy | None = None,
) -> ShadowMonitoringSnapshot:
    """Build a bounded operational-health snapshot from persisted runs."""
    policy = policy or ShadowMonitoringPolicy()
    scoped = [r for r in runs if admission_id is None or r.get("admission_id") == admission_id]
    total = len(scoped)
    successful = sum(r.get("status") == "SHADOW_OK" for r in scoped)
    errors = total - successful
    latencies: list[float] = []
    case_ids: set[str] = set()
    safety_violations = 0
    review_violations = 0
    identities: set[tuple[str, str, str]] = set()

    for row in scoped:
        case_id = str(row.get("case_id", "")).strip()
        if case_id:
            case_ids.add(case_id)
        try:
            latency = float(row.get("latency_ms", 0.0))
            if math.isfinite(latency) and latency >= 0:
                latencies.append(latency)
        except (TypeError, ValueError):
            pass

        identities.add((
            str(row.get("provider", "")),
            str(row.get("model_version", "")),
            str(row.get("adapter_name", "")),
        ))

        if row.get("human_review_required") is not True:
            review_violations += 1

        if row.get("status") == "SHADOW_OK":
            output = row.get("output")
            if not isinstance(output, dict):
                safety_violations += 1
            else:
                if validate_advisory_output(output):
                    safety_violations += 1
                if output.get("human_review_required") is not True:
                    review_violations += 1

    identity_violations = max(0, len(identities) - 1)
    error_rate = errors / total if total else 0.0
    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)

    alerts: list[str] = []
    if total < policy.minimum_runs_for_stability:
        alerts.append("INSUFFICIENT_SHADOW_RUNS")
    if error_rate > policy.maximum_error_rate:
        alerts.append("ERROR_RATE_ABOVE_POLICY")
    if p95 > policy.maximum_p95_latency_ms:
        alerts.append("P95_LATENCY_ABOVE_POLICY")
    if review_violations:
        alerts.append("HUMAN_REVIEW_CONTRACT_VIOLATION")
    if safety_violations:
        alerts.append("SAFETY_CONTRACT_VIOLATION")
    if identity_violations:
        alerts.append("MODEL_IDENTITY_DRIFT")

    if safety_violations or review_violations or identity_violations:
        status = "CONTROL_REQUIRED"
    elif total < policy.minimum_runs_for_stability:
        status = "NOT_ENOUGH_DATA"
    elif error_rate > policy.maximum_error_rate or p95 > policy.maximum_p95_latency_ms:
        status = "WATCH"
    else:
        status = "HEALTHY_WITHIN_SHADOW_POLICY"

    first = scoped[0] if scoped else {}
    return ShadowMonitoringSnapshot(
        admission_id=admission_id,
        provider=first.get("provider") if first else None,
        model_version=first.get("model_version") if first else None,
        adapter_name=first.get("adapter_name") if first else None,
        policy_version=POLICY_VERSION,
        total_runs=total,
        successful_runs=successful,
        error_runs=errors,
        unique_cases=len(case_ids),
        error_rate=error_rate,
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        human_review_contract_violations=review_violations,
        identity_consistency_violations=identity_violations,
        safety_contract_violations=safety_violations,
        status=status,
        alerts=tuple(alerts),
    )
