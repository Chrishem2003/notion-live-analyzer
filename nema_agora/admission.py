"""Phase 16 benchmark governance and model-admission gate.

Admission is evidence governance for controlled shadow evaluation only. It is
not NEMA approval, regulatory authorization, environmental truth, enforcement
authorization, emergency dispatch permission, or production certification.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import uuid
import re
from typing import Any

from nema_agora.evaluation import validate_advisory_output


POLICY_VERSION = "phase16-v1"
ADMITTED = "ADMITTED_FOR_CONTROLLED_SHADOW"
NOT_ADMITTED = "NOT_ADMITTED"


@dataclass(frozen=True)
class ModelAdmissionPolicy:
    minimum_cases: int = 25
    minimum_category_accuracy: float = 0.80
    minimum_duplicate_f1: float = 0.80
    minimum_category_kappa: float = 0.80
    require_zero_failures: bool = True
    require_all_disagreements_adjudicated: bool = True


@dataclass(frozen=True)
class ModelCandidate:
    provider: str
    model_version: str
    adapter_name: str
    intended_use: str
    data_handling: str
    retention_policy: str
    processing_location: str
    failure_behaviour: str

    def __post_init__(self) -> None:
        fields = {
            "provider": self.provider, "model_version": self.model_version,
            "adapter_name": self.adapter_name, "intended_use": self.intended_use,
            "data_handling": self.data_handling, "retention_policy": self.retention_policy,
            "processing_location": self.processing_location,
            "failure_behaviour": self.failure_behaviour,
        }
        for name, value in fields.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
            if len(value) > 500:
                raise ValueError(f"{name} is too long")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdmissionDecision:
    admission_id: str
    candidate: ModelCandidate
    dataset_version: str
    manifest_hash: str
    comparison_run_id: str
    decision: str
    gates: dict[str, bool]
    approver_id: str
    rationale: str
    created_at: str
    policy_version: str = POLICY_VERSION
    safety_notice: str = (
        "Admission permits controlled shadow evaluation only. It does not "
        "establish environmental truth, official incident status, regulatory "
        "priority, NEMA endorsement, enforcement authority, emergency response "
        "authority, or production approval."
    )

    def __post_init__(self) -> None:
        if self.decision not in {ADMITTED, NOT_ADMITTED}:
            raise ValueError("Unsupported admission decision")
        for name, value in {
            "admission_id": self.admission_id,
            "dataset_version": self.dataset_version,
            "manifest_hash": self.manifest_hash,
            "comparison_run_id": self.comparison_run_id,
            "approver_id": self.approver_id,
            "rationale": self.rationale,
        }.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if len(self.rationale) > 1500:
            raise ValueError("rationale must be 1,500 characters or fewer")
        if not isinstance(self.gates, dict) or not self.gates:
            raise ValueError("gates are required")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["candidate"] = self.candidate.to_dict()
        return d


def _gate(value: bool) -> bool:
    return bool(value)


def _comparison_metrics(comparison: dict[str, Any], candidate: ModelCandidate) -> dict[str, Any] | None:
    dataset = comparison.get("dataset") or {}
    if not isinstance(dataset, dict):
        return None
    adapters = comparison.get("adapters") or []
    matches = [
        m for m in adapters
        if isinstance(m, dict)
        and m.get("adapter") == candidate.adapter_name
        and m.get("provider") == candidate.provider
        and m.get("model_version") == candidate.model_version
    ]
    return matches[0] if len(matches) == 1 else None


def evaluate_admission(
    *,
    candidate: ModelCandidate,
    dataset: dict[str, Any],
    annotation_readiness: dict[str, Any],
    comparison: dict[str, Any],
    comparison_run_id: str,
    approver_id: str,
    rationale: str,
    policy: ModelAdmissionPolicy | None = None,
) -> AdmissionDecision:
    """Evaluate one evidence bundle and fail closed on any binding mismatch."""
    policy = policy or ModelAdmissionPolicy()
    if not approver_id.strip():
        raise ValueError("Explicit approver identity is required")
    if not rationale.strip():
        raise ValueError("Admission rationale is required")
    if not comparison_run_id.strip():
        raise ValueError("comparison_run_id is required")

    dataset_version = str(dataset.get("dataset_version", "")).strip()
    manifest_hash = str(dataset.get("manifest_hash", "")).strip()
    required_annotation_gates = {"minimum_double_annotated_cases", "two_independent_annotators", "all_annotator_pairs_measured", "minimum_category_kappa", "all_disagreements_adjudicated"}
    ann_gates = annotation_readiness.get("gates") or {}
    annotation_gate_evidence = {key: ann_gates.get(key) is True for key in required_annotation_gates}
    comparison_dataset = comparison.get("dataset") or {}
    metrics = _comparison_metrics(comparison, candidate)
    unresolved = annotation_readiness.get("unresolved_disagreements") or []
    cases = int(dataset.get("cases", 0) or 0)

    gates = {
        "frozen_dataset": bool(dataset_version and re.fullmatch(r"[0-9a-fA-F]{64}", manifest_hash) and cases > 0),
        "minimum_cases": cases >= policy.minimum_cases,
        "annotation_ready": annotation_readiness.get("status") == "READY_FOR_REVIEW" and all(annotation_gate_evidence.values()),
        "annotation_category_kappa": float(annotation_readiness.get("minimum_category_kappa", 0.0) or 0.0) >= policy.minimum_category_kappa,
        "all_disagreements_adjudicated": not unresolved,
        "comparison_run_match": bool(
            comparison.get("run_id") == comparison_run_id
            and comparison_dataset.get("dataset_version") == dataset_version
            and comparison_dataset.get("manifest_hash") == manifest_hash
        ),
        "model_identity_match": metrics is not None,
        "comparison_ready": comparison.get("readiness") == "READY_FOR_REVIEW",
        "zero_failures": bool(metrics is not None and metrics.get("failures", 1) == 0),
        "category_accuracy": bool(metrics is not None and float(metrics.get("category_accuracy", 0.0)) >= policy.minimum_category_accuracy),
        "duplicate_f1": bool(metrics is not None and float(metrics.get("duplicate_f1", 0.0)) >= policy.minimum_duplicate_f1),
        "human_review_contract": False,
    }

    # Require explicit safety evidence from every available case result for
    # this adapter. A merely non-empty notice is not sufficient.
    case_results = comparison.get("case_results") or []
    candidate_rows = [
        r for r in case_results
        if isinstance(r, dict) and r.get("adapter") == candidate.adapter_name and r.get("provider") == candidate.provider and r.get("model_version") == candidate.model_version
    ]
    if candidate_rows:
        safety_ok = True
        for row in candidate_rows:
            output = row.get("output")
            if isinstance(output, dict):
                safety_errors = validate_advisory_output(output)
                if safety_errors or output.get("human_review_required") is not True:
                    safety_ok = False
            elif row.get("status") != "OK":
                safety_ok = False
        gates["human_review_contract"] = safety_ok
    else:
        gates["human_review_contract"] = False

    # These policy flags are represented explicitly so future policy changes
    # cannot silently weaken the decision.
    gates["policy_zero_failures_enabled"] = (not policy.require_zero_failures) or gates["zero_failures"]
    gates["policy_adjudication_enabled"] = (
        (not policy.require_all_disagreements_adjudicated)
        or gates["all_disagreements_adjudicated"]
    )

    passed = all(gates.values())
    return AdmissionDecision(
        admission_id=f"ADM-{uuid.uuid4().hex[:10].upper()}",
        candidate=candidate,
        dataset_version=dataset_version,
        manifest_hash=manifest_hash,
        comparison_run_id=comparison_run_id,
        decision=ADMITTED if passed else NOT_ADMITTED,
        gates={k: _gate(v) for k, v in gates.items()},
        approver_id=approver_id.strip(),
        rationale=rationale.strip(),
        created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
    )


def serialise_admission(decision: AdmissionDecision) -> str:
    return json.dumps(decision.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class AdmissionStore:
    """SQLite-backed immutable admission decision history."""
    def __init__(self, database_path: str):
        import sqlite3
        self.database_path = str(database_path)
        with sqlite3.connect(self.database_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS model_admissions (
                admission_id TEXT PRIMARY KEY,
                actor_id TEXT NOT NULL,
                approver_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                model_version TEXT NOT NULL,
                adapter_name TEXT NOT NULL,
                dataset_version TEXT NOT NULL,
                manifest_hash TEXT NOT NULL,
                comparison_run_id TEXT NOT NULL,
                decision TEXT NOT NULL CHECK (decision IN ('ADMITTED_FOR_CONTROLLED_SHADOW','NOT_ADMITTED')),
                policy_version TEXT NOT NULL,
                rationale TEXT NOT NULL,
                created_at TEXT NOT NULL,
                result_json TEXT NOT NULL
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_model_admissions_time ON model_admissions(created_at, admission_id)")

    def save(self, decision: AdmissionDecision, *, actor_id: str) -> None:
        import sqlite3
        if not actor_id.strip():
            raise ValueError("Authenticated actor is required")
        with sqlite3.connect(self.database_path) as db:
            db.execute(
                """INSERT INTO model_admissions
                (admission_id, actor_id, approver_id, provider, model_version,
                 adapter_name, dataset_version, manifest_hash, comparison_run_id,
                 decision, policy_version, rationale, created_at, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    decision.admission_id, actor_id, decision.approver_id,
                    decision.candidate.provider, decision.candidate.model_version,
                    decision.candidate.adapter_name, decision.dataset_version,
                    decision.manifest_hash, decision.comparison_run_id,
                    decision.decision, decision.policy_version, decision.rationale,
                    decision.created_at, serialise_admission(decision),
                ),
            )

    def list(self, *, limit: int = 25) -> list[dict[str, Any]]:
        import sqlite3
        safe_limit = max(1, min(int(limit), 100))
        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                """SELECT admission_id, actor_id, approver_id, provider,
                          model_version, adapter_name, dataset_version,
                          manifest_hash, comparison_run_id, decision,
                          policy_version, rationale, created_at, result_json
                   FROM model_admissions
                   ORDER BY created_at DESC, admission_id DESC LIMIT ?""",
                (safe_limit,),
            ).fetchall()
        return [{**dict(r), "result": json.loads(r["result_json"])} for r in rows]
