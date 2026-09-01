from __future__ import annotations

import re

from .models import ProblemContext


class ProblemContextClassifier:
    """Classify a user problem into a useful optimization context."""

    _TYPE_KEYWORDS = {
        "coding": {
            "code",
            "coding",
            "program",
            "programming",
            "python",
            "javascript",
            "typescript",
            "bug",
            "debug",
            "software",
            "api",
            "function",
            "repository",
            "github",
        },
        "research": {
            "research",
            "investigate",
            "sources",
            "literature",
            "study",
            "evidence",
            "compare",
            "findings",
        },
        "planning": {
            "plan",
            "planning",
            "roadmap",
            "strategy",
            "schedule",
            "project",
            "implementation",
            "steps",
        },
        "reasoning": {
            "why",
            "explain",
            "reason",
            "logic",
            "solve",
            "deduce",
            "evaluate",
            "prove",
            "calculate",
        },
        "analysis": {
            "analyze",
            "analysis",
            "analyse",
            "diagnose",
            "inspect",
            "review",
            "assess",
            "evaluate",
            "performance",
        },
    }

    _COMPLEXITY_MARKERS = {
        "complex",
        "architecture",
        "architectural",
        "integrate",
        "integration",
        "multiple",
        "dependencies",
        "constraint",
        "constraints",
        "compare",
        "verify",
        "verification",
        "optimize",
        "optimization",
        "root",
        "cause",
        "system",
        "pipeline",
        "design",
        "implementation",
        "production",
        "security",
        "performance",
    }

    def classify(self, prompt: str) -> ProblemContext:
        if not prompt or not prompt.strip():
            raise ValueError(
                "Problem prompt cannot be empty."
            )

        normalized = prompt.lower()

        words = set(
            re.findall(
                r"[a-zA-Z0-9_]+",
                normalized,
            )
        )

        scores = {}

        for problem_type, keywords in self._TYPE_KEYWORDS.items():
            scores[problem_type] = sum(
                1
                for keyword in keywords
                if keyword in words
            )

        if not any(scores.values()):
            problem_type = "general"
        else:
            problem_type = max(
                scores,
                key=scores.get,
            )

        complexity = self._complexity(
            prompt=prompt,
            words=words,
            scores=scores,
        )

        return ProblemContext(
            problem_type=problem_type,
            complexity=complexity,
            requires_reasoning=(
                scores.get("reasoning", 0) > 0
                or problem_type == "reasoning"
            ),
            requires_code=(
                scores.get("coding", 0) > 0
                or problem_type == "coding"
            ),
            requires_research=(
                scores.get("research", 0) > 0
                or problem_type == "research"
            ),
            requires_planning=(
                scores.get("planning", 0) > 0
                or problem_type == "planning"
            ),
            requires_analysis=(
                scores.get("analysis", 0) > 0
                or problem_type == "analysis"
            ),
            keywords=sorted(
                word
                for word in words
                if any(
                    word in keywords
                    for keywords in self._TYPE_KEYWORDS.values()
                )
            ),
            metadata={
                "scores": scores,
                "word_count": len(words),
            },
        )

    @classmethod
    def _complexity(
        cls,
        prompt: str,
        words: set[str],
        scores: dict[str, int],
    ) -> float:
        word_count = len(words)

        length_signal = min(
            1.0,
            word_count / 80.0,
        )

        sentence_count = max(
            1,
            len(
                re.findall(
                    r"[.!?]+",
                    prompt,
                )
            ),
        )

        sentence_signal = min(
            1.0,
            sentence_count / 6.0,
        )

        marker_count = sum(
            1
            for marker in cls._COMPLEXITY_MARKERS
            if marker in words
        )

        marker_signal = min(
            1.0,
            marker_count / 8.0,
        )

        type_signal = min(
            1.0,
            sum(scores.values()) / 8.0,
        )

        reasoning_signal = min(
            1.0,
            (
                scores.get("reasoning", 0)
                + scores.get("analysis", 0)
                + scores.get("planning", 0)
            ) / 6.0,
        )

        complexity = (
            length_signal * 0.20
            + sentence_signal * 0.15
            + marker_signal * 0.30
            + type_signal * 0.15
            + reasoning_signal * 0.20
        )

        return round(
            min(1.0, complexity),
            4,
        )
