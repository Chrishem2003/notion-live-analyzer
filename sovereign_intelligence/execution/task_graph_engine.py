from __future__ import annotations

from collections import defaultdict

from .task_graph import TaskGraph, TaskNode


class TaskGraphEngine:

    def validate(
        self,
        graph: TaskGraph,
    ):

        ids = {
            task.id
            for task in graph.tasks
        }

        for task in graph.tasks:

            for dependency in task.dependencies:

                if dependency not in ids:

                    raise ValueError(
                        f"Task '{task.id}' depends "
                        f"on unknown task "
                        f"'{dependency}'."
                    )

        self._detect_cycles(graph)

        return True

    def _detect_cycles(
        self,
        graph: TaskGraph,
    ):

        state = {}

        def visit(task_id):

            current = state.get(
                task_id,
                0,
            )

            if current == 1:

                raise ValueError(
                    "Task graph contains "
                    "a dependency cycle."
                )

            if current == 2:
                return

            state[task_id] = 1

            task = graph.get(task_id)

            if task:

                for dependency in task.dependencies:

                    visit(dependency)

            state[task_id] = 2

        for task in graph.tasks:
            visit(task.id)

    def ready(
        self,
        graph: TaskGraph,
    ) -> list[TaskNode]:

        self.validate(graph)

        ready_tasks = []

        completed = {
            task.id
            for task in graph.tasks
            if task.status == "completed"
        }

        for task in graph.tasks:

            if task.status != "pending":
                continue

            if all(
                dependency in completed
                for dependency
                in task.dependencies
            ):

                ready_tasks.append(task)

        return sorted(
            ready_tasks,
            key=lambda task: task.priority,
        )

    def complete(
        self,
        graph: TaskGraph,
        task_id: str,
        result=None,
    ):

        task = graph.get(task_id)

        if task is None:

            raise KeyError(
                f"Unknown task: {task_id}"
            )

        task.status = "completed"
        task.result = result
        task.error = None

    def fail(
        self,
        graph: TaskGraph,
        task_id: str,
        error: str,
    ):

        task = graph.get(task_id)

        if task is None:

            raise KeyError(
                f"Unknown task: {task_id}"
            )

        task.status = "failed"
        task.error = error

    def is_complete(
        self,
        graph: TaskGraph,
    ):

        return all(
            task.status == "completed"
            for task in graph.tasks
        )
