from __future__ import annotations

import re

from .decision_models import AgentVote, DecisionResult


class DecisionEngine:

    def decide(self, contributions) -> DecisionResult:

        successful = [
            item
            for item in contributions
            if getattr(item, "success", False)
            and str(getattr(item, "answer", "")).strip()
        ]

        if not successful:
            return DecisionResult(
                decision="No reliable decision could be reached.",
                confidence=0.0,
                consensus=False,
                rationale="No successful specialist contributions.",
            )

        votes = []

        for item in successful:

            answer = str(item.answer).strip()

            position = self._extract_position(answer)

            confidence = float(
                max(
                    0.0,
                    min(
                        1.0,
                        getattr(
                            item,
                            "confidence",
                            0.5,
                        ),
                    ),
                )
            )

            votes.append(
                AgentVote(
                    agent=str(item.agent),
                    position=position,
                    confidence=confidence,
                    evidence=answer,
                )
            )

        groups = {}

        for vote in votes:
            key = vote.position.lower().strip()
            groups.setdefault(key, []).append(vote)

        ranked = sorted(
            groups.items(),
            key=lambda pair: (
                sum(v.confidence for v in pair[1]),
                len(pair[1]),
            ),
            reverse=True,
        )

        winner_key, winner_votes = ranked[0]

        total_weight = sum(
            vote.confidence
            for vote in votes
        )

        winner_weight = sum(
            vote.confidence
            for vote in winner_votes
        )

        confidence = (
            winner_weight / total_weight
            if total_weight
            else 0.0
        )

        conflicts = []

        if len(ranked) > 1:

            for key, group in ranked[1:]:

                conflicts.append(
                    "Conflict between "
                    f"'{winner_key}' and '{key}' "
                    f"from {len(group)} specialist(s)."
                )

        consensus = (
            len(ranked) == 1
            or confidence >= 0.70
        )

        decision = winner_key

        rationale = self._build_rationale(
            votes,
            winner_votes,
            confidence,
            conflicts,
        )

        return DecisionResult(
            decision=decision,
            confidence=confidence,
            consensus=consensus,
            votes=votes,
            conflicts=conflicts,
            rationale=rationale,
            metadata={
                "specialists": len(votes),
                "positions": len(ranked),
            },
        )

    @staticmethod
    def _extract_position(answer: str) -> str:

        lines = [
            line.strip()
            for line in answer.splitlines()
            if line.strip()
        ]

        if not lines:
            return "No conclusion."

        for line in lines:

            match = re.match(
                r"^(?:conclusion|decision|recommendation)"
                r"\s*:\s*(.+)$",
                line,
                flags=re.IGNORECASE,
            )

            if match:
                return match.group(1).strip()

        return lines[0][:300]

    @staticmethod
    def _build_rationale(
        votes,
        winner_votes,
        confidence,
        conflicts,
    ):

        agents = ", ".join(
            vote.agent
            for vote in winner_votes
        )

        text = (
            f"Leading conclusion supported by: {agents}. "
            f"Weighted confidence: {confidence:.3f}."
        )

        if conflicts:
            text += (
                " Conflicting specialist findings were "
                "retained for review."
            )

        return text
