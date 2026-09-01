from __future__ import annotations

import re
import uuid

from ..models import Problem, Plan, PlanStep


class Planner:

    def build(self, problem: Problem) -> Plan:

        text = problem.original.lower()

        steps = []

        if any(
            word in text
            for word in [
                "research",
                "latest",
                "current",
                "find",
                "compare",
            ]
        ):
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Identify required evidence and research questions.",
                    agent="research",
                )
            )

        if any(
            word in text
            for word in [
                "code",
                "python",
                "software",
                "repository",
                "bug",
                "error",
            ]
        ):
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Analyze the software problem and implementation constraints.",
                    agent="coding",
                )
            )

        if any(
            word in text
            for word in [
                "calculate",
                "equation",
                "math",
                "percentage",
                "statistics",
            ]
        ):
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Perform and verify quantitative reasoning.",
                    agent="mathematics",
                )
            )

        if any(
            word in text
            for word in [
                "cad",
                "geometry",
                "design",
                "structural",
            ]
        ):
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Analyze engineering or CAD-specific constraints.",
                    agent="engineering",
                )
            )

        if not steps:
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Analyze the problem and determine the most appropriate solution path.",
                    agent="general",
                )
            )

        steps.append(
            PlanStep(
                id=str(uuid.uuid4()),
                description="Critically review the proposed solution.",
                agent="general",
            )
        )

        return Plan(
            objective=problem.objective,
            steps=steps,
            rationale="Plan generated from the problem's intent and constraints.",
        )