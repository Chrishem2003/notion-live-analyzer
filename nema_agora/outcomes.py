"""Phase 28 controlled outcome study.

Pairs baseline and assisted observations by scenario to make workflow-effect
comparisons reproducible. Results are software-performance evidence only.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib, json, uuid
from typing import Any

from nema_agora.impact import ImpactObservation

POLICY_VERSION = "phase28-v1"

@dataclass(frozen=True)
class OutcomePair:
    pair_id: str
    scenario_id: str
    baseline_id: str
    assisted_id: str
    synthetic: bool = True
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class OutcomeStudy:
    study_id: str
    pairs: tuple[OutcomePair, ...]
    sample_size: int
    metrics: dict[str, Any]
    dataset_fingerprint: str
    created_at: str
    policy_version: str = POLICY_VERSION
    decision_notice: str = (
        "Controlled outcome evidence measures workflow behaviour only; it does not "
        "establish environmental impact, environmental truth, regulatory status, "
        "NEMA authorization, production approval, or autonomous decision authority."
    )
    def to_dict(self): return asdict(self)

def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

def pair_observations(observations: list[ImpactObservation]) -> tuple[OutcomePair, ...]:
    baseline={o.scenario_id:o for o in observations if o.condition=="BASELINE"}
    assisted={o.scenario_id:o for o in observations if o.condition=="ASSISTED"}
    pairs=[]
    for scenario_id in sorted(set(baseline) & set(assisted)):
        pairs.append(OutcomePair(
            pair_id="OP-" + _fingerprint({"scenario_id": scenario_id, "baseline_id": baseline[scenario_id].observation_id, "assisted_id": assisted[scenario_id].observation_id})[:16].upper(),
            scenario_id=scenario_id,
            baseline_id=baseline[scenario_id].observation_id,
            assisted_id=assisted[scenario_id].observation_id,
        ))
    return tuple(pairs)

def build_outcome_study(observations: list[ImpactObservation]) -> OutcomeStudy:
    pairs=pair_observations(observations)
    by_id={o.observation_id:o for o in observations}
    paired=[(by_id[p.baseline_id],by_id[p.assisted_id]) for p in pairs]
    def mean_delta(getter):
        vals=[float(getter(a))-float(getter(b)) for b,a in paired]
        return sum(vals)/len(vals) if vals else None
    def rate_delta(getter):
        vals=[(1.0 if getter(a) else 0.0)-(1.0 if getter(b) else 0.0) for b,a in paired]
        return sum(vals)/len(vals) if vals else None
    metrics={
        "paired_cases": len(paired),
        "time_to_review_delta_assisted_minus_baseline": mean_delta(lambda o:o.review_seconds),
        "evidence_completeness_delta": rate_delta(lambda o:o.evidence_complete),
        "duplicate_detection_delta": rate_delta(lambda o:o.duplicate_correct),
        "reviewer_workload_delta": mean_delta(lambda o:o.reviewer_actions),
        "correction_rate_delta": rate_delta(lambda o:o.corrected),
        "end_to_end_success_delta": rate_delta(lambda o:o.workflow_success),
    }
    payload={"pairs":[p.to_dict() for p in pairs],"observations":[o.to_dict() for o in observations]}
    return OutcomeStudy(
        study_id=f"OS-{uuid.uuid4().hex[:10].upper()}",
        pairs=pairs, sample_size=len(paired), metrics=metrics,
        dataset_fingerprint=_fingerprint(payload),
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )

def validate_outcome_study(study: OutcomeStudy, observations: list[ImpactObservation]) -> dict[str, Any]:
    ids={o.observation_id:o for o in observations}
    errors=[]
    for pair in study.pairs:
        b,a=ids.get(pair.baseline_id),ids.get(pair.assisted_id)
        if not b or not a: errors.append(f"MISSING_OBSERVATION:{pair.scenario_id}")
        elif b.condition!="BASELINE" or a.condition!="ASSISTED": errors.append(f"CONDITION_MISMATCH:{pair.scenario_id}")
        elif b.scenario_id!=a.scenario_id or b.scenario_id!=pair.scenario_id: errors.append(f"SCENARIO_MISMATCH:{pair.scenario_id}")
    return {"valid":not errors and study.sample_size==len(study.pairs), "errors":errors,
            "paired_cases":len(study.pairs), "policy_version":POLICY_VERSION,
            "decision_notice":study.decision_notice}
