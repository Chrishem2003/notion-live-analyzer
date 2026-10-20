"""Phase 12 controlled AI shadow mode.

Runs an advisory model beside the existing human workflow without allowing
the model to mutate observations, workflow state, or official decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from time import perf_counter
from typing import Any

from nema_agora.ai_adapter import AdvisoryModelAdapter, validate_model_result


@dataclass(frozen=True)
class ShadowResult:
    source_case_id: str
    provider: str
    model_version: str
    status: str
    latency_ms: float
    output: dict[str, Any] | None
    error: str | None
    human_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _bounded_error(exc: Exception) -> str:
    return str(exc).strip()[:500] or exc.__class__.__name__


def run_shadow(record: dict[str, Any], adapter: AdvisoryModelAdapter) -> ShadowResult:
    """Execute an advisory model beside a case and return an isolated result.

    The input record is never modified. Adapter output is safety-validated and
    must remain bound to the source case. Adapter failures become an auditable
    SHADOW_ERROR result rather than changing the case workflow.
    """
    case_id = str(record.get("case_id", "")).strip()
    if not case_id or len(case_id) > 64:
        raise ValueError("A valid source case identifier is required.")

    provider = str(getattr(adapter, "provider", "unknown")).strip()[:80] or "unknown"
    model_version = str(getattr(adapter, "model_version", "unknown")).strip()[:120] or "unknown"

    started = perf_counter()
    try:
        output = adapter.analyse(dict(record))
        validated = validate_model_result(record, output)
    except Exception as exc:
        latency_ms = round((perf_counter() - started) * 1000, 3)
        return ShadowResult(
            source_case_id=case_id,
            provider=provider,
            model_version=model_version,
            status="SHADOW_ERROR",
            latency_ms=latency_ms,
            output=None,
            error=_bounded_error(exc),
        )

    latency_ms = round((perf_counter() - started) * 1000, 3)
    return ShadowResult(
        source_case_id=case_id,
        provider=provider,
        model_version=model_version,
        status="SHADOW_OK",
        latency_ms=latency_ms,
        output=dict(validated),
        error=None,
        human_review_required=True,
    )


class DeterministicShadowAdapter:
    """Local zero-provider adapter for exercising shadow infrastructure.

    It intentionally reuses the deterministic Phase 8 advisory engine. This
    is a harness, not evidence that an external AI model has been evaluated.
    """

    provider = "local-deterministic"
    model_version = "phase12-deterministic-shadow-v1"

    def analyse(self, record: dict[str, Any]) -> dict[str, Any]:
        from nema_agora.intelligence import analyze_observation

        analysis = analyze_observation(record, peer_records=[])
        return {
            "source_case_id": record.get("case_id"),
            "summary": analysis["summary"],
            "category_suggestions": analysis["category_suggestions"],
            "priority_advisory": analysis["priority_advisory"],
            "quality_status": analysis["quality_status"],
            "quality_flags": analysis["quality_flags"],
            "human_review_required": True,
            "decision_notice": analysis["decision_notice"],
        }
