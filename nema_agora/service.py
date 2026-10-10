"""Principal-bound application service for NEMA-AGORA.

The Streamlit page should interact with this layer instead of supplying
arbitrary actor IDs or roles to the persistence repository.
"""
from __future__ import annotations

import csv
import io
from typing import Any
from dataclasses import asdict

from nema_agora.access import has_permission, require_permission
from nema_agora.identity import Principal
from nema_agora.intelligence import analyze_observation
from nema_agora.copilot import build_reviewer_copilot
from nema_agora.storage import NemaAgoraRepository
from nema_agora.shadow import DeterministicShadowAdapter, run_shadow
from nema_agora.lab import EvaluationRunStore, LabResult
from nema_agora.comparison import ComparisonRunStore, ComparisonResult
from nema_agora.admission import AdmissionStore, ModelAdmissionPolicy, ModelCandidate, evaluate_admission
from nema_agora.shadow_governance import ControlledShadowStore, execute_controlled_shadow
from nema_agora.shadow_monitoring import build_shadow_monitoring_snapshot
from nema_agora.provenance import ProvenanceStore, verify_provenance_chain
from nema_agora.field_eval import (
    FieldScenario, FieldEvaluationStore, evaluate_scenario,
    build_controlled_scenarios, run_field_evaluation,
)
from nema_agora.accessibility import AccessibilityStore, AccessibilityObservation, make_observation, summarise
from nema_agora.review_governance import (
    ReviewStore, build_reevaluation, make_shadow_review, make_lifecycle_decision,
)
from nema_agora.annotation import AnnotationStore, annotation_readiness, make_annotation, make_adjudication, pairwise_agreement, disagreement_cases
from nema_agora.governance_decision_ledger import GovernanceDecisionLedger


class NemaAgoraService:
    """Authorize application operations using an authenticated Principal."""

    def __init__(self, repository: NemaAgoraRepository):
        self.repository = repository

    @staticmethod
    def _authorised(principal: Principal) -> None:
        if not principal.is_authorised or not principal.role:
            raise PermissionError("Authenticated user is not provisioned for NEMA-AGORA.")

    def create_observation(self, record: dict[str, Any], principal: Principal) -> dict[str, Any]:
        self._authorised(principal)
        stored_record = dict(record)
        # Ownership is derived from the authenticated principal, never from
        # caller-controlled record data.
        stored_record["owner_id"] = principal.subject_key
        return self.repository.create_observation(
            stored_record, actor_id=principal.subject_key, role=principal.role
        )

    def list_observations(self, principal: Principal, status: str | None = None) -> list[dict[str, Any]]:
        self._authorised(principal)
        return self.repository.list_observations(
            actor_id=principal.subject_key, role=principal.role, status=status
        )

    def get_observation(self, case_id: str, principal: Principal) -> dict[str, Any] | None:
        self._authorised(principal)
        return self.repository.get_observation(
            case_id, actor_id=principal.subject_key, role=principal.role
        )

    def update_review(
        self,
        case_id: str,
        principal: Principal,
        *,
        new_status: str,
        review_notes: str,
        changed_at: str,
    ) -> dict[str, Any]:
        self._authorised(principal)
        return self.repository.update_review(
            case_id,
            actor_id=principal.subject_key,
            role=principal.role,
            new_status=new_status,
            review_notes=review_notes,
            changed_at=changed_at,
        )

    def list_audit_events(self, case_id: str, principal: Principal) -> list[dict[str, Any]]:
        self._authorised(principal)
        return self.repository.list_audit_events(
            case_id, actor_id=principal.subject_key, role=principal.role
        )

    def record_operation(self, principal: Principal, *, operation: str, occurred_at: str, details: dict[str, Any] | None = None) -> None:
        self._authorised(principal)
        self.repository.record_operation(
            actor_id=principal.subject_key, role=principal.role,
            operation=operation, occurred_at=occurred_at, details=details,
        )

    def list_operation_events(self, principal: Principal, *, limit: int = 100) -> list[dict[str, Any]]:
        self._authorised(principal)
        return self.repository.list_operation_events(
            actor_id=principal.subject_key, role=principal.role, limit=limit
        )

    def analyze_observation(self, record: dict[str, Any], principal: Principal, *, peer_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Run advisory evidence intelligence under the authenticated principal."""
        self._authorised(principal)
        require_permission(principal.role, "intelligence:use")
        analysis = analyze_observation(record, peer_records=peer_records)
        try:
            self.repository.record_intelligence_event(
                str(record.get("case_id", "")),
                actor_id=principal.subject_key,
                role=principal.role,
                event_type="analysis_run",
                occurred_at=__import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
                details={"copilot_version": "phase10-v1"},
            )
        except KeyError:
            # Pure/unit analysis may operate on an unsaved synthetic record.
            # Persisted pilot cases are always audit-tracked.
            pass
        return analysis

    def build_reviewer_copilot(
        self,
        record: dict[str, Any],
        principal: Principal,
        *,
        peer_records: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:use")
        analysis = self.analyze_observation(record, principal, peer_records=peer_records)
        return build_reviewer_copilot(record, analysis)

    def run_shadow(
        self,
        record: dict[str, Any],
        principal: Principal,
        *,
        adapter: Any | None = None,
    ) -> dict[str, Any]:
        """Run an isolated advisory model beside the existing workflow."""
        self._authorised(principal)
        require_permission(principal.role, "intelligence:shadow")
        shadow_result = run_shadow(
            record,
            adapter if adapter is not None else DeterministicShadowAdapter(),
        )
        payload = shadow_result.to_dict()
        self.repository.record_shadow_run(
            str(record.get("case_id", "")),
            actor_id=principal.subject_key,
            role=principal.role,
            result=payload,
            occurred_at=__import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        return payload

    def list_shadow_runs(self, case_id: str, principal: Principal) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:shadow")
        return self.repository.list_shadow_runs(
            case_id, actor_id=principal.subject_key, role=principal.role
        )

    def build_observatory_snapshot(
        self,
        principal: Principal,
        report: Any,
        feedback_events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "metrics:read")
        from nema_agora.observatory import build_observatory_snapshot
        return build_observatory_snapshot(report, feedback_events).to_dict()

    def create_annotation(
        self,
        *,
        case_id: str,
        principal: Principal,
        dataset_version: str,
        category: str,
        duplicate: bool,
        summary_faithful: bool | None,
        notes: str = "",
    ) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "annotation:create")
        annotation = make_annotation(
            case_id=case_id,
            annotator_id=principal.subject_key,
            dataset_version=dataset_version,
            category=category,
            duplicate=duplicate,
            summary_faithful=summary_faithful,
            notes=notes,
        )
        AnnotationStore(self.repository.database_path).save(annotation)
        return annotation.to_dict()

    def list_own_annotations(self, principal: Principal, dataset_version: str) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "annotation:read_own")
        return [a.to_dict() for a in AnnotationStore(self.repository.database_path).list_for_annotator(principal.subject_key, dataset_version)]

    def annotation_agreement(self, principal: Principal, dataset_version: str) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "annotation:read_all")
        store = AnnotationStore(self.repository.database_path)
        rows = store.list_all(dataset_version)
        annotators = sorted({a.annotator_id for a in rows})
        if len(annotators) < 2:
            return {"annotators": annotators, "agreement": None, "disagreements": disagreement_cases(rows)}
        first = [a for a in rows if a.annotator_id == annotators[0]]
        second = [a for a in rows if a.annotator_id == annotators[1]]
        return {
            "annotators": annotators,
            "agreement": pairwise_agreement(first, second),
            "disagreements": disagreement_cases(rows),
        }

    def annotation_readiness(self, principal: Principal, dataset_version: str) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "annotation:read_all")
        store = AnnotationStore(self.repository.database_path)
        return annotation_readiness(
            store.list_all(dataset_version),
            store.list_adjudications(dataset_version),
        )

    def list_case_annotations(self, case_id: str, principal: Principal, dataset_version: str) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "annotation:read_all")
        return [a.to_dict() for a in AnnotationStore(self.repository.database_path).list_for_case(case_id, dataset_version)]

    def adjudicate_annotation(
        self,
        *,
        case_id: str,
        principal: Principal,
        dataset_version: str,
        final_category: str,
        final_duplicate: bool,
        final_summary_faithful: bool | None,
        rationale: str,
    ) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "annotation:adjudicate")
        item = make_adjudication(
            case_id=case_id,
            adjudicator_id=principal.subject_key,
            dataset_version=dataset_version,
            final_category=final_category,
            final_duplicate=final_duplicate,
            final_summary_faithful=final_summary_faithful,
            rationale=rationale,
        )
        AnnotationStore(self.repository.database_path).save_adjudication(item)
        return asdict(item)

    def list_adjudications(self, principal: Principal, dataset_version: str) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "annotation:read_all")
        return [a.__dict__ for a in AnnotationStore(self.repository.database_path).list_adjudications(dataset_version)]

    def evaluate_model_admission(
        self,
        *,
        candidate: ModelCandidate,
        dataset: dict[str, Any],
        annotation_readiness: dict[str, Any],
        comparison: dict[str, Any],
        comparison_run_id: str,
        principal: Principal,
        approver_id: str,
        rationale: str,
        policy: ModelAdmissionPolicy | None = None,
    ) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:admit_model")
        if approver_id.strip() != principal.subject_key:
            raise PermissionError("Approver identity must match the authenticated principal.")
        decision = evaluate_admission(
            candidate=candidate, dataset=dataset,
            annotation_readiness=annotation_readiness, comparison=comparison,
            comparison_run_id=comparison_run_id, approver_id=approver_id,
            rationale=rationale, policy=policy,
        )
        AdmissionStore(self.repository.database_path).save(decision, actor_id=principal.subject_key)
        return decision.to_dict()

    def execute_controlled_shadow(
        self,
        *,
        record: dict[str, Any],
        admission_id: str,
        principal: Principal,
        adapter: Any,
    ) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:controlled_shadow")
        result = execute_controlled_shadow(
            database_path=self.repository.database_path,
            record=record,
            admission_id=admission_id,
            actor_id=principal.subject_key,
            adapter=adapter,
        )
        return result.to_dict()

    def list_controlled_shadow_runs(
        self, principal: Principal, *, admission_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:controlled_shadow")
        return ControlledShadowStore(self.repository.database_path).list(
            admission_id=admission_id, limit=limit
        )

    def list_model_admissions(self, principal: Principal, *, limit: int = 25) -> list[dict[str, Any]]:
        self._authorised(principal)
        if not (
            principal.role
            and (
                has_permission(principal.role, "intelligence:admit_model")
                or has_permission(principal.role, "intelligence:monitor")
            )
        ):
            raise PermissionError("Role is not permitted to inspect model admissions.")
        return AdmissionStore(self.repository.database_path).list(limit=limit)

    def build_shadow_monitoring_snapshot(
        self,
        principal: Principal,
        *,
        admission_id: str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:monitor")
        runs = ControlledShadowStore(self.repository.database_path).list(
            admission_id=admission_id, limit=limit
        )
        return build_shadow_monitoring_snapshot(
            runs, admission_id=admission_id
        ).to_dict()

    def run_controlled_field_evaluation(self, principal: Principal) -> dict[str, Any]:
        """Execute the deterministic synthetic Phase 21 scenario suite end-to-end."""
        self._authorised(principal)
        require_permission(principal.role, "intelligence:field_eval")
        results = run_field_evaluation(scenarios=build_controlled_scenarios())
        store = FieldEvaluationStore(self.repository.database_path)
        for result in results:
            store.save(result)
        from nema_agora.field_eval import summarise_results
        return summarise_results(results)

    def record_field_evaluation(self, principal: Principal, *, scenario: FieldScenario, observed: dict[str, Any], notes: str = "") -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:field_eval")
        result = evaluate_scenario(scenario=scenario, observed=observed, notes=notes)
        FieldEvaluationStore(self.repository.database_path).save(result)
        return result.to_dict()

    def record_accessibility_observation(self, principal: Principal, *, scenario_id: str, channel: str, outcome: str, steps_completed: int, steps_expected: int, accessibility_barrier: bool, review_required: bool, notes: str = "") -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:impact")
        row = make_observation(scenario_id=scenario_id, channel=channel, outcome=outcome,
            steps_completed=steps_completed, steps_expected=steps_expected,
            accessibility_barrier=accessibility_barrier, review_required=review_required, notes=notes)
        AccessibilityStore(self.repository.database_path).save(row)
        return row.to_dict()

    def list_accessibility_observations(self, principal: Principal, *, limit: int = 1000) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:impact")
        return AccessibilityStore(self.repository.database_path).list(limit)

    def list_field_evaluations(self, principal: Principal, *, limit: int = 500) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:field_eval")
        return FieldEvaluationStore(self.repository.database_path).list(limit=limit)

    def list_provenance(
        self,
        principal: Principal,
        *,
        event_type: str | None = None,
        event_id: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:provenance")
        return ProvenanceStore(self.repository.database_path).list(
            event_type=event_type, event_id=event_id, limit=limit
        )

    def verify_provenance(
        self,
        principal: Principal,
        *,
        event_type: str | None = None,
        limit: int = 1000,
    ) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:provenance")
        records = ProvenanceStore(self.repository.database_path).list(
            event_type=event_type, limit=limit
        )
        return verify_provenance_chain(records)

    def record_shadow_review(
        self, principal: Principal, *, run: dict[str, Any], decision: str,
        corrected_category: str | None = None, notes: str = "",
    ) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:review_shadow")
        if not str(run.get("run_id", "")).strip() or not str(run.get("admission_id", "")).strip():
            raise ValueError("Shadow run must contain run_id and admission_id.")
        review = make_shadow_review(
            run=run, reviewer_id=principal.subject_key, decision=decision,
            corrected_category=corrected_category, notes=notes,
        )
        ReviewStore(self.repository.database_path).save_review(review)
        review_decision = {
            "CONFIRMED_USEFUL": "APPROVE",
            "UNSAFE": "REJECT",
            "NEEDS_CORRECTION": "HUMAN_REVIEW_REQUIRED",
            "NOT_APPLICABLE": "DEFER",
        }[review.decision]
        self._record_governance_event(
            decision_kind="review_decision", principal=principal,
            artifact_id=review.review_id, status="COMPLETED",
            decision=review_decision, reason_code="HUMAN_REVIEW",
        )
        return review.to_dict()

    def list_shadow_reviews(
        self, principal: Principal, *, admission_id: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:review_shadow")
        return ReviewStore(self.repository.database_path).list_reviews(
            admission_id=admission_id, limit=limit
        )

    def build_reevaluation(
        self, principal: Principal, *, admission_id: str | None = None, limit: int = 500
    ) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:review_shadow")
        runs = ControlledShadowStore(self.repository.database_path).list(
            admission_id=admission_id, limit=limit
        )
        reviews = ReviewStore(self.repository.database_path).list_reviews(
            admission_id=admission_id, limit=limit
        )
        return build_reevaluation(runs, reviews, admission_id=admission_id)

    def record_lifecycle_decision(
        self, principal: Principal, *, admission: dict[str, Any], action: str,
        rationale: str, evidence_snapshot: dict[str, Any]
    ) -> dict[str, Any]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:govern_shadow")
        decision = make_lifecycle_decision(
            admission=admission, action=action, decided_by=principal.subject_key,
            rationale=rationale, evidence_snapshot=evidence_snapshot,
        )
        ReviewStore(self.repository.database_path).save_lifecycle_decision(decision)
        lifecycle_decision = {
            "RETAIN": "APPROVE",
            "SUSPEND": "REJECT",
            "REVIEW": "DEFER",
            "RE_ADMIT_REQUIRED": "DEFER",
        }[decision.action]
        self._record_governance_event(
            decision_kind="lifecycle_decision", principal=principal,
            artifact_id=decision.decision_id, status="COMPLETED",
            decision=lifecycle_decision, reason_code="HUMAN_LIFECYCLE_DECISION",
        )
        return decision.to_dict()

    def list_lifecycle_decisions(
        self, principal: Principal, *, admission_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:review_shadow")
        return ReviewStore(self.repository.database_path).list_lifecycle_decisions(
            admission_id=admission_id, limit=limit
        )

    def record_comparison_run(self, result: ComparisonResult, principal: Principal) -> None:
        """Persist a Phase 15 comparison result under the authenticated actor."""
        self._authorised(principal)
        require_permission(principal.role, "intelligence:comparison")
        ComparisonRunStore(self.repository.database_path).save(result, actor_id=principal.subject_key)

    def list_comparison_runs(self, principal: Principal, *, limit: int = 25) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:comparison")
        return ComparisonRunStore(self.repository.database_path).list(limit=limit)

    def record_evaluation_run(self, result: LabResult, principal: Principal) -> None:
        """Persist an immutable Phase 13 evaluation result under the authenticated actor."""
        self._authorised(principal)
        require_permission(principal.role, "intelligence:lab")
        EvaluationRunStore(self.repository.database_path).save(
            result, actor_id=principal.subject_key
        )
        self._record_governance_event(
            decision_kind="evaluation_completed", principal=principal,
            artifact_id=str(result.run_id), status="COMPLETED",
            decision="HUMAN_REVIEW_REQUIRED", reason_code="EVALUATION_COMPLETE",
        )

    def list_evaluation_runs(self, principal: Principal, *, limit: int = 25) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:lab")
        return EvaluationRunStore(self.repository.database_path).list(limit=limit)

    def record_intelligence_feedback(
        self,
        case_id: str,
        principal: Principal,
        *,
        feedback: dict[str, Any],
        occurred_at: str,
    ) -> None:
        self._authorised(principal)
        require_permission(principal.role, "intelligence:feedback")
        self.repository.record_intelligence_feedback(
            case_id,
            actor_id=principal.subject_key,
            role=principal.role,
            feedback=feedback,
            occurred_at=occurred_at,
        )

    def list_intelligence_events(
        self, case_id: str, principal: Principal
    ) -> list[dict[str, Any]]:
        self._authorised(principal)
        require_permission(principal.role, "audit:read")
        return self.repository.list_intelligence_events(
            case_id, actor_id=principal.subject_key, role=principal.role
        )

    def export_csv(self, principal: Principal, records: list[dict[str, Any]]) -> bytes:
        self._authorised(principal)
        require_permission(principal.role, "case:export")
        fields = [
            "case_id", "created_at", "observation_date", "category", "severity",
            "district_or_site", "description", "latitude", "longitude", "status",
            "review_notes", "evidence_reference",
        ]
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = {key: record.get(key, "") for key in fields}
            # Spreadsheet formula neutralisation is deliberately retained.
            for key, value in row.items():
                if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
                    row[key] = "'" + value
            writer.writerow(row)
        return buffer.getvalue().encode("utf-8-sig")
