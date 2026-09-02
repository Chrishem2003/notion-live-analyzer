"""Discovery-to-evidence pipeline engine."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sovereign_intelligence.research.discovery.engine import (
    SourceDiscoveryEngine,
)
from sovereign_intelligence.research.discovery.models import (
    DiscoveryPlan,
    SourceCandidate,
)
from sovereign_intelligence.research.discovery.planner import plan_discovery
from sovereign_intelligence.research.intake.engine import EvidenceIntakeEngine
from sovereign_intelligence.research.intake.models import IntakeRequest

from .models import PipelineResult


class ResearchPipelineEngine:
    """
    Coordinate research discovery with evidence intake.

    This layer does not perform network access itself. Discovery adapters
    remain responsible for obtaining actual source candidates.
    """

    def __init__(
        self,
        discovery_engine: SourceDiscoveryEngine | None = None,
        intake_engine: EvidenceIntakeEngine | None = None,
    ) -> None:
        self.discovery_engine = (
            discovery_engine or SourceDiscoveryEngine()
        )
        self.intake_engine = (
            intake_engine or EvidenceIntakeEngine()
        )

    def discover(
        self,
        query: str,
        *,
        plan: DiscoveryPlan | None = None,
    ):
        """Create or accept a plan, then execute source discovery."""
        active_plan = plan or plan_discovery(query)

        return (
            active_plan,
            self.discovery_engine.discover(active_plan),
        )

    @staticmethod
    def _candidate_to_request(
        candidate: SourceCandidate,
    ) -> IntakeRequest | None:
        """
        Convert candidate metadata containing source material into intake data.

        Discovery candidates describe sources. Evidence intake requires actual
        content, so candidates without content are rejected honestly.
        """
        metadata = candidate.metadata

        content = metadata.get("content")

        if content is None:
            return None

        content = str(content).strip()

        if not content:
            return None

        title = candidate.title.strip() or candidate.source_id

        return IntakeRequest(
            source_id=candidate.source_id,
            source=candidate.source,
            source_type=candidate.source_type,
            title=title,
            content=content,
            location=candidate.location,
            metadata=dict(metadata),
        )

    def intake_candidates(
        self,
        candidates: Iterable[SourceCandidate],
    ):
        """Convert candidates carrying actual content into evidence."""
        requests: list[IntakeRequest] = []

        for candidate in candidates:
            request = self._candidate_to_request(candidate)

            if request is not None:
                requests.append(request)

        return self.intake_engine.intake_many(requests)

    def run(
        self,
        query: str,
        *,
        plan: DiscoveryPlan | None = None,
    ) -> PipelineResult:
        """Run discovery followed by evidence intake."""
        active_plan, discovery = self.discover(
            query,
            plan=plan,
        )

        intake_requests: list[IntakeRequest] = []
        rejected: list[dict[str, Any]] = []

        for candidate in discovery.candidates:
            request = self._candidate_to_request(candidate)

            if request is None:
                rejected.append(
                    {
                        "source_id": candidate.source_id,
                        "reason": "candidate_has_no_source_content",
                        "source_type": candidate.source_type,
                    }
                )
                continue

            intake_requests.append(request)

        intake_result = self.intake_engine.intake_many(
            intake_requests
        )

        rejected.extend(
            dict(item)
            for item in intake_result.rejected
        )

        return PipelineResult(
            query=query,
            plan=active_plan,
            discovery=discovery,
            evidence=tuple(intake_result.records),
            rejected=tuple(rejected),
            metadata={
                "discovery_candidates": len(
                    discovery.candidates
                ),
                "intake_requests": len(
                    intake_requests
                ),
                "accepted_evidence": intake_result.accepted_count,
                "rejected_sources": len(rejected),
            },
        )
