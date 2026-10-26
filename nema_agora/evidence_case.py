"""Deterministic, human-governed evidence case/provenance bundle for NEMA-AGORA."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any, Mapping

POLICY_VERSION = "evidence-case-v1"
ALLOWED_STATES = {"DRAFT", "READY_FOR_REVIEW", "REVIEWED", "EXPORTED"}
ALLOWED_DECISIONS = {"PENDING", "ACKNOWLEDGED", "REQUIRES_FOLLOW_UP", "ESCALATED"}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _utc(value: str | None = None) -> str:
    return value or datetime.now(timezone.utc).isoformat()


def _provenance_payload(
    case_id: str,
    observation_fingerprint: str,
    evidence: tuple["EvidenceReference", ...],
    findings: tuple["AdvisoryFinding", ...],
) -> dict[str, Any]:
    return {
        "policy_version": POLICY_VERSION,
        "case_id": case_id,
        "observation_fingerprint": observation_fingerprint,
        "evidence": [asdict(item) for item in evidence],
        "findings": [asdict(item) for item in findings],
    }


def _review_fingerprint(review: "HumanReview") -> str:
    return _fingerprint({"policy_version": POLICY_VERSION, "human_review": asdict(review)})


def _has_timezone(value: str) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except (TypeError, ValueError, OverflowError):
        return False


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    kind: str
    source: str
    captured_at: str
    content_fingerprint: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdvisoryFinding:
    finding_id: str
    model_id: str
    model_version: str
    summary: str
    confidence: float | None
    input_fingerprints: tuple[str, ...]
    generated_at: str
    advisory_only: bool = True


@dataclass(frozen=True)
class HumanReview:
    reviewer_id: str
    role: str
    decision: str
    reviewed_at: str
    notes: str = ""


@dataclass(frozen=True)
class EvidenceCase:
    case_id: str
    created_at: str
    state: str
    observation_fingerprint: str
    evidence: tuple[EvidenceReference, ...]
    findings: tuple[AdvisoryFinding, ...] = ()
    review: HumanReview | None = None
    provenance_fingerprint: str = ""
    review_fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_evidence_case(
    *,
    case_id: str,
    observation: Mapping[str, Any],
    evidence: list[EvidenceReference] | tuple[EvidenceReference, ...],
    findings: list[AdvisoryFinding] | tuple[AdvisoryFinding, ...] = (),
    created_at: str | None = None,
) -> EvidenceCase:
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("case_id is required")
    if not isinstance(observation, Mapping):
        raise ValueError("observation must be a mapping")
    try:
        _canonical(observation)
    except (TypeError, ValueError):
        raise ValueError("observation must be JSON serializable") from None
    if not isinstance(evidence, (tuple, list)):
        raise ValueError("evidence must be a list or tuple")
    if not isinstance(findings, (tuple, list)):
        raise ValueError("findings must be a list or tuple")
    refs = tuple(evidence)
    findings_tuple = tuple(findings)
    if any(not isinstance(reference, EvidenceReference) for reference in refs):
        raise ValueError("evidence entries must be EvidenceReference values")
    if any(not isinstance(finding, AdvisoryFinding) for finding in findings_tuple):
        raise ValueError("findings entries must be AdvisoryFinding values")
    for reference in refs:
        if not all(isinstance(value, str) and value.strip() for value in (
            reference.evidence_id, reference.kind, reference.source, reference.content_fingerprint
        )):
            raise ValueError("evidence references require id, kind, source, and content fingerprint")
        if not _has_timezone(reference.captured_at):
            raise ValueError("evidence captured_at must be an ISO 8601 timestamp with timezone")
        if not isinstance(reference.metadata, Mapping):
            raise ValueError("evidence metadata must be a mapping")
        try:
            _canonical(reference.metadata)
        except (TypeError, ValueError):
            raise ValueError("evidence metadata must be JSON serializable") from None
    evidence_ids = [reference.evidence_id for reference in refs]
    if len(set(evidence_ids)) != len(evidence_ids):
        raise ValueError("evidence_id values must be unique")
    for finding in findings_tuple:
        if not all(isinstance(value, str) and value.strip() for value in (
            finding.finding_id, finding.model_id, finding.model_version, finding.summary
        )):
            raise ValueError("advisory findings require id, model, version, and summary")
        if not _has_timezone(finding.generated_at):
            raise ValueError("finding generated_at must be an ISO 8601 timestamp with timezone")
        if not isinstance(finding.input_fingerprints, (tuple, list)) or any(
            not isinstance(item, str) or not item.strip() for item in finding.input_fingerprints
        ):
            raise ValueError("finding input fingerprints must be non-empty strings")
    for finding in findings_tuple:
        if finding.advisory_only is not True:
            raise ValueError("findings must remain advisory_only")
        if finding.confidence is not None:
            try:
                confidence_valid = (
                    not isinstance(finding.confidence, bool)
                    and isinstance(finding.confidence, (int, float))
                    and math.isfinite(finding.confidence)
                    and 0 <= finding.confidence <= 1
                )
            except (TypeError, ValueError):
                confidence_valid = False
            if not confidence_valid:
                raise ValueError("confidence must be between 0 and 1")
    created = _utc(created_at)
    if not _has_timezone(created):
        raise ValueError("created_at must be an ISO 8601 timestamp with timezone")
    observation_fingerprint = _fingerprint(observation)
    provenance_fingerprint = _fingerprint(
        _provenance_payload(case_id, observation_fingerprint, refs, findings_tuple)
    )
    return EvidenceCase(
        case_id, created, "READY_FOR_REVIEW", observation_fingerprint,
        refs, findings_tuple, None, provenance_fingerprint
    )


def attach_human_review(
    case: EvidenceCase,
    *,
    reviewer_id: str,
    role: str,
    decision: str,
    reviewed_at: str | None = None,
    notes: str = "",
) -> EvidenceCase:
    if case.state not in {"READY_FOR_REVIEW", "REVIEWED"}:
        raise ValueError("case is not reviewable in its current state")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip() or not isinstance(role, str) or not role.strip():
        raise ValueError("reviewer_id and role are required")
    if not isinstance(decision, str) or decision not in ALLOWED_DECISIONS - {"PENDING"}:
        raise ValueError("invalid human review decision")
    if not isinstance(notes, str):
        raise ValueError("review notes must be text")
    timestamp = _utc(reviewed_at)
    if not _has_timezone(timestamp):
        raise ValueError("reviewed_at must be an ISO 8601 timestamp with timezone")
    review = HumanReview(reviewer_id, role, decision, timestamp, notes)
    return EvidenceCase(
        case.case_id, case.created_at, "REVIEWED", case.observation_fingerprint,
        case.evidence, case.findings, review, case.provenance_fingerprint,
        _review_fingerprint(review)
    )


def mark_exported(case: EvidenceCase) -> EvidenceCase:
    validation = validate_evidence_case(case)
    if not validation["valid"]:
        raise ValueError("evidence case failed integrity validation: " + ", ".join(validation["issues"]))
    if case.state != "REVIEWED" or case.review is None:
        raise ValueError("only human-reviewed cases can be exported")
    return EvidenceCase(
        case.case_id, case.created_at, "EXPORTED", case.observation_fingerprint,
        case.evidence, case.findings, case.review, case.provenance_fingerprint,
        case.review_fingerprint
    )


def evidence_case_from_dict(payload: Mapping[str, Any]) -> EvidenceCase:
    """Rehydrate a persisted JSON bundle into validated immutable domain objects."""
    if not isinstance(payload, Mapping):
        raise ValueError("persisted evidence case must be a mapping")
    try:
        evidence = tuple(EvidenceReference(**item) for item in payload["evidence"])
        findings = tuple(
            AdvisoryFinding(
                **{**item, "input_fingerprints": tuple(item["input_fingerprints"])}
            )
            for item in payload.get("findings", [])
        )
        review_payload = payload.get("review")
        review = HumanReview(**review_payload) if isinstance(review_payload, Mapping) else None
        return EvidenceCase(
            case_id=payload["case_id"],
            created_at=payload["created_at"],
            state=payload["state"],
            observation_fingerprint=payload["observation_fingerprint"],
            evidence=evidence,
            findings=findings,
            review=review,
            provenance_fingerprint=payload["provenance_fingerprint"],
            review_fingerprint=payload.get("review_fingerprint", ""),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("persisted evidence case has an invalid schema") from exc


def validate_evidence_case(case: EvidenceCase) -> dict[str, Any]:
    issues: list[str] = []
    if not isinstance(case, EvidenceCase):
        return {
            "policy_version": POLICY_VERSION, "case_id": None, "state": None,
            "valid": False, "issues": ["invalid_case_type"],
            "human_governed": True, "automatic_repair": False,
            "execution_gate": "CLOSED", "environmental_truth_claim": False,
            "regulatory_conclusion": False, "nema_authorization": False,
            "emergency_dispatch": False,
        }
    if not isinstance(case.state, str) or case.state not in ALLOWED_STATES:
        issues.append("invalid_state")
    if (
        not isinstance(case.case_id, str) or not case.case_id.strip()
        or not isinstance(case.observation_fingerprint, str)
        or not case.observation_fingerprint.strip()
    ):
        issues.append("missing_identity")
    if not _has_timezone(case.created_at):
        issues.append("invalid_created_at")
    evidence_items = case.evidence if isinstance(case.evidence, (tuple, list)) else ()
    if not isinstance(case.evidence, (tuple, list)):
        issues.append("invalid_evidence_collection")
    if any(not isinstance(reference, EvidenceReference) for reference in evidence_items):
        issues.append("invalid_evidence_reference")
    valid_references = [reference for reference in evidence_items if isinstance(reference, EvidenceReference)]
    evidence_ids = [
        reference.evidence_id for reference in valid_references
        if isinstance(reference.evidence_id, str) and reference.evidence_id.strip()
    ]
    if len(set(evidence_ids)) != len(evidence_ids):
        issues.append("duplicate_evidence_id")
    for reference in valid_references:
        if not all(isinstance(value, str) and value.strip() for value in (
            reference.evidence_id, reference.kind, reference.source, reference.content_fingerprint
        )):
            issues.append("invalid_evidence_reference")
        if not _has_timezone(reference.captured_at):
            issues.append("invalid_evidence_timestamp")
    finding_items = case.findings if isinstance(case.findings, (tuple, list)) else ()
    if not isinstance(case.findings, (tuple, list)):
        issues.append("invalid_findings_collection")
    if any(not isinstance(finding, AdvisoryFinding) for finding in finding_items):
        issues.append("invalid_advisory_finding")
    for finding in (item for item in finding_items if isinstance(item, AdvisoryFinding)):
        if finding.advisory_only is not True:
            issues.append("non_advisory_finding")
        if finding.confidence is not None:
            try:
                confidence_valid = (
                    not isinstance(finding.confidence, bool)
                    and isinstance(finding.confidence, (int, float))
                    and math.isfinite(finding.confidence)
                    and 0 <= finding.confidence <= 1
                )
            except (TypeError, ValueError):
                confidence_valid = False
            if not confidence_valid:
                issues.append("invalid_confidence")
        if not _has_timezone(finding.generated_at):
            issues.append("invalid_finding_timestamp")
        if not isinstance(finding.input_fingerprints, (tuple, list)) or any(
            not isinstance(item, str) or not item.strip() for item in finding.input_fingerprints
        ):
            issues.append("invalid_input_fingerprints")
    try:
        expected_provenance = _fingerprint(
            _provenance_payload(case.case_id, case.observation_fingerprint, case.evidence, case.findings)
        )
        if not case.provenance_fingerprint or case.provenance_fingerprint != expected_provenance:
            issues.append("provenance_fingerprint_mismatch")
    except (TypeError, ValueError):
        issues.append("provenance_payload_invalid")
    if isinstance(case.state, str) and case.state in {"REVIEWED", "EXPORTED"} and case.review is None:
        issues.append("review_missing")
    if case.review is not None and not isinstance(case.review, HumanReview):
        issues.append("invalid_review_type")
    if isinstance(case.review, HumanReview):
        if (
            not isinstance(case.review.reviewer_id, str) or not case.review.reviewer_id.strip()
            or not isinstance(case.review.role, str) or not case.review.role.strip()
        ):
            issues.append("invalid_reviewer_identity")
        if not isinstance(case.review.decision, str) or case.review.decision not in ALLOWED_DECISIONS - {"PENDING"}:
            issues.append("invalid_review_decision")
        if not _has_timezone(case.review.reviewed_at):
            issues.append("invalid_review_timestamp")
        if not isinstance(case.review.notes, str):
            issues.append("invalid_review_notes")
        try:
            expected_review_fingerprint = _review_fingerprint(case.review)
            if not case.review_fingerprint or case.review_fingerprint != expected_review_fingerprint:
                issues.append("review_fingerprint_mismatch")
        except (TypeError, ValueError):
            issues.append("review_payload_invalid")
    elif case.review_fingerprint:
        issues.append("orphan_review_fingerprint")
    return {
        "policy_version": POLICY_VERSION,
        "case_id": case.case_id,
        "state": case.state,
        "valid": not issues,
        "issues": sorted(set(issues)),
        "human_governed": True,
        "automatic_repair": False,
        "execution_gate": "CLOSED",
        "environmental_truth_claim": False,
        "regulatory_conclusion": False,
        "nema_authorization": False,
        "emergency_dispatch": False,
    }
