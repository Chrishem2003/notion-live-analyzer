"""Principal-bound application service for NEMA-AGORA.

The Streamlit page should interact with this layer instead of supplying
arbitrary actor IDs or roles to the persistence repository.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from nema_agora.access import require_permission
from nema_agora.identity import Principal
from nema_agora.intelligence import analyze_observation
from nema_agora.copilot import build_reviewer_copilot
from nema_agora.storage import NemaAgoraRepository


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
