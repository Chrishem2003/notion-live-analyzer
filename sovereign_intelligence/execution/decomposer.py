from __future__ import annotations

import uuid

from ..models import Problem
from .task_graph import (
    TaskGraph,
    TaskNode,
)


class ProblemDecomposer:

    def _task(
        self,
        title,
        objective,
        agent="general",
        dependencies=None,
        priority=100,
    ):

        return TaskNode(
            id=str(uuid.uuid4()),
            title=title,
            objective=objective,
            agent=agent,
            dependencies=(
                dependencies
                or []
            ),
            priority=priority,
        )

    def decompose(
        self,
        problem: Problem,
    ) -> TaskGraph:

        text = problem.original.lower()

        tasks = []

        understanding = self._task(
            title="Understand problem",
            objective=(
                "Extract the user's objective, "
                "constraints, assumptions and "
                "success criteria."
            ),
            agent="general",
            priority=10,
        )

        tasks.append(
            understanding
        )

        analysis = self._task(
            title="Analyze problem",
            objective=(
                "Analyze the problem and identify "
                "the technical or conceptual "
                "requirements."
            ),
            agent="general",
            dependencies=[
                understanding.id
            ],
            priority=20,
        )

        tasks.append(
            analysis
        )

        if any(
            word in text
            for word in [
                "research",
                "latest",
                "current",
                "compare",
                "source",
                "evidence",
            ]
        ):

            tasks.append(
                self._task(
                    title="Research evidence",
                    objective=(
                        "Identify and evaluate "
                        "relevant evidence."
                    ),
                    agent="research",
                    dependencies=[
                        analysis.id
                    ],
                    priority=30,
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
                "program",
            ]
        ):

            tasks.append(
                self._task(
                    title="Engineering analysis",
                    objective=(
                        "Analyze implementation "
                        "requirements and technical "
                        "constraints."
                    ),
                    agent="coding",
                    dependencies=[
                        analysis.id
                    ],
                    priority=30,
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

            tasks.append(
                self._task(
                    title="Quantitative analysis",
                    objective=(
                        "Perform quantitative "
                        "reasoning and verify "
                        "calculations."
                    ),
                    agent="mathematics",
                    dependencies=[
                        analysis.id
                    ],
                    priority=30,
                )
            )

        if any(
            word in text
            for word in [
                "cad",
                "geometry",
                "engineering",
                "structural",
                "design",
            ]
        ):

            tasks.append(
                self._task(
                    title="Engineering design analysis",
                    objective=(
                        "Analyze geometry, design "
                        "and engineering constraints."
                    ),
                    agent="engineering",
                    dependencies=[
                        analysis.id
                    ],
                    priority=30,
                )
            )

        final_dependencies = [
            task.id
            for task in tasks
            if task.id != understanding.id
            and task.id != analysis.id
        ]

        if not final_dependencies:

            final_dependencies = [
                analysis.id
            ]

        tasks.append(
            self._task(
                title="Synthesize solution",
                objective=(
                    "Combine the completed analyses "
                    "into a coherent solution."
                ),
                agent="general",
                dependencies=final_dependencies,
                priority=80,
            )
        )

        tasks.append(
            self._task(
                title="Verify solution",
                objective=(
                    "Critically review the solution "
                    "for errors, unsupported claims "
                    "and unmet requirements."
                ),
                agent="general",
                dependencies=[
                    tasks[-1].id
                ],
                priority=90,
            )
        )

        return TaskGraph(
            objective=problem.objective,
            tasks=tasks,
            metadata={
                "decomposer": (
                    "sovereign_problem_decomposer"
                )
            },
        )
