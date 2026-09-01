from __future__ import annotations

from typing import Any, Callable

from .team_models import (
    AgentContribution,
    TeamResult,
)


DEFAULT_TEAM = (
    ("research", "Research specialist"),
    ("coding", "Software engineering specialist"),
    ("mathematics", "Mathematical reasoning specialist"),
    ("engineering", "Engineering specialist"),
    ("general", "General reasoning specialist"),
)


class MultiAgentTeam:

    def __init__(
        self,
        agents=None,
        max_agents: int = 5,
    ):
        self.agents = tuple(agents or DEFAULT_TEAM)
        self.max_agents = max(1, max_agents)

    def select_agents(self, problem: str):
        text = problem.lower()

        selected = []

        keyword_map = {
            "research": (
                "research",
                "latest",
                "current",
                "source",
                "evidence",
                "compare",
                "find",
            ),
            "coding": (
                "code",
                "python",
                "software",
                "bug",
                "error",
                "repository",
                "api",
                "program",
            ),
            "mathematics": (
                "calculate",
                "equation",
                "math",
                "percentage",
                "statistics",
                "formula",
            ),
            "engineering": (
                "cad",
                "geometry",
                "engineering",
                "design",
                "structural",
                "architecture",
            ),
            "general": (
                "explain",
                "solve",
                "plan",
                "strategy",
                "decision",
            ),
        }

        for name, role in self.agents:

            keywords = keyword_map.get(name, ())

            if any(word in text for word in keywords):
                selected.append((name, role))

        if not selected:
            selected = list(self.agents)

        if ("general", "General reasoning specialist") not in selected:
            selected.append(
                ("general", "General reasoning specialist")
            )

        return selected[:self.max_agents]

    def execute(
        self,
        problem: str,
        worker: Callable[[str, str, str], Any],
    ) -> TeamResult:

        selected = self.select_agents(problem)

        result = TeamResult(
            objective=problem
        )

        for name, role in selected:

            prompt = self._build_prompt(
                problem,
                name,
                role,
            )

            try:

                raw = worker(
                    name,
                    role,
                    prompt,
                )

                answer = self._extract_answer(raw)

                if answer.strip():

                    confidence = self._estimate_confidence(
                        answer
                    )

                    result.contributions.append(
                        AgentContribution(
                            agent=name,
                            role=role,
                            success=True,
                            answer=answer,
                            confidence=confidence,
                        )
                    )

                    result.successful_agents += 1

                else:

                    result.contributions.append(
                        AgentContribution(
                            agent=name,
                            role=role,
                            success=False,
                            error="Agent returned an empty response.",
                        )
                    )

                    result.failed_agents += 1

            except Exception as exc:

                result.contributions.append(
                    AgentContribution(
                        agent=name,
                        role=role,
                        success=False,
                        error=str(exc),
                    )
                )

                result.failed_agents += 1

        result.disagreements = self._detect_disagreements(
            result.contributions
        )

        result.consensus = self._aggregate(
            problem,
            result.contributions,
        )

        result.confidence = self._team_confidence(
            result
        )

        return result

    @staticmethod
    def _build_prompt(
        problem: str,
        agent: str,
        role: str,
    ) -> str:

        return (
            "You are participating in a multi-agent "
            "problem-solving team.\n\n"
            f"Your specialist role: {role}\n"
            f"Agent identity: {agent}\n\n"
            "Analyze the problem independently.\n"
            "Separate facts from assumptions.\n"
            "Do not invent evidence or tool execution.\n"
            "Give concrete, useful conclusions.\n\n"
            f"Problem:\n{problem}"
        )

    @staticmethod
    def _extract_answer(raw: Any) -> str:

        if raw is None:
            return ""

        if isinstance(raw, str):
            return raw

        if hasattr(raw, "text"):
            return str(raw.text)

        if hasattr(raw, "answer"):
            return str(raw.answer)

        return str(raw)

    @staticmethod
    def _estimate_confidence(answer: str) -> float:

        text = answer.strip()

        if not text:
            return 0.0

        certainty_penalties = (
            "maybe",
            "possibly",
            "uncertain",
            "i think",
            "not sure",
        )

        penalty = sum(
            0.08
            for phrase in certainty_penalties
            if phrase in text.lower()
        )

        return max(
            0.50,
            min(0.95, 0.85 - penalty),
        )

    @staticmethod
    def _detect_disagreements(contributions):

        successful = [
            item
            for item in contributions
            if item.success
        ]

        disagreements = []

        if len(successful) < 2:
            return disagreements

        answers = [
            item.answer.lower()
            for item in successful
        ]

        contradiction_pairs = (
            ("yes", "no"),
            ("true", "false"),
            ("recommended", "not recommended"),
            ("safe", "unsafe"),
            ("valid", "invalid"),
        )

        for first, second in contradiction_pairs:

            has_first = any(
                first in answer
                for answer in answers
            )

            has_second = any(
                second in answer
                for answer in answers
            )

            if has_first and has_second:
                disagreements.append(
                    f"Potential disagreement involving "
                    f"'{first}' and '{second}'."
                )

        return disagreements

    @staticmethod
    def _aggregate(problem, contributions):

        successful = [
            item
            for item in contributions
            if item.success and item.answer.strip()
        ]

        if not successful:
            return ""

        if len(successful) == 1:
            return successful[0].answer

        sections = [
            "Multi-agent synthesis for the requested problem.",
            "",
            "Independent specialist findings:",
            "",
        ]

        for item in successful:

            sections.append(
                f"[{item.role}]\n"
                f"{item.answer.strip()}\n"
            )

        sections.append(
            "Synthesis requirement:\n"
            "Use the strongest compatible conclusions from "
            "the specialist findings. Preserve disagreements "
            "instead of hiding them. Do not claim independent "
            "verification unless it actually occurred."
        )

        return "\n".join(sections)

    @staticmethod
    def _team_confidence(result):

        successful = [
            item
            for item in result.contributions
            if item.success
        ]

        if not successful:
            return 0.0

        average = sum(
            item.confidence
            for item in successful
        ) / len(successful)

        success_ratio = (
            result.successful_agents
            / max(
                1,
                result.successful_agents
                + result.failed_agents,
            )
        )

        disagreement_penalty = min(
            0.15,
            len(result.disagreements) * 0.05,
        )

        return max(
            0.0,
            min(
                1.0,
                average
                * success_ratio
                - disagreement_penalty,
            ),
        )
