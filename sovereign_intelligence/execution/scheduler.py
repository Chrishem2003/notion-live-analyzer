from __future__ import annotations

import time
from datetime import datetime, timezone

from .task_graph import TaskGraph
from .task_graph_engine import TaskGraphEngine

from .scheduler_models import (
    ExecutionPolicy,
    ExecutionReport,
    TaskExecutionRecord,
)


class ExecutionScheduler:

    def __init__(
        self,
        policy: ExecutionPolicy | None = None,
    ):

        self.policy = (
            policy
            or ExecutionPolicy()
        )

        self.graph_engine = (
            TaskGraphEngine()
        )

    def _timestamp(self):

        return datetime.now(
            timezone.utc
        ).isoformat()

    def run(
        self,
        graph: TaskGraph,
        executor,
    ):

        self.graph_engine.validate(
            graph
        )

        report = ExecutionReport(
            status="running"
        )

        while not self.graph_engine.is_complete(
            graph
        ):

            ready = self.graph_engine.ready(
                graph
            )

            if not ready:

                pending = [
                    task
                    for task in graph.tasks
                    if task.status == "pending"
                ]

                if pending:

                    for task in pending:

                        task.status = "skipped"

                        report.skipped.append(
                            task.id
                        )

                    report.status = "failed"

                    return report

                break

            task = ready[0]

            success = False

            for attempt in range(
                1,
                self.policy.max_retries + 2,
            ):

                started = self._timestamp()

                start_time = time.monotonic()

                task.status = "running"

                try:

                    result = executor(
                        task
                    )

                    duration = (
                        time.monotonic()
                        - start_time
                    )

                    finished = (
                        self._timestamp()
                    )

                    record = (
                        TaskExecutionRecord(
                            task_id=task.id,
                            attempt=attempt,
                            status="completed",
                            started_at=started,
                            finished_at=finished,
                            duration_seconds=duration,
                            result=result,
                        )
                    )

                    report.records.append(
                        record
                    )

                    self.graph_engine.complete(
                        graph,
                        task.id,
                        result,
                    )

                    report.completed.append(
                        task.id
                    )

                    success = True

                    break

                except Exception as exc:

                    duration = (
                        time.monotonic()
                        - start_time
                    )

                    finished = (
                        self._timestamp()
                    )

                    record = (
                        TaskExecutionRecord(
                            task_id=task.id,
                            attempt=attempt,
                            status="failed",
                            started_at=started,
                            finished_at=finished,
                            duration_seconds=duration,
                            error=str(exc),
                        )
                    )

                    report.records.append(
                        record
                    )

                    task.status = "pending"

                    if (
                        attempt
                        > self.policy.max_retries
                    ):

                        self.graph_engine.fail(
                            graph,
                            task.id,
                            str(exc),
                        )

                        report.failed.append(
                            task.id
                        )

                        if (
                            self.policy.stop_on_failure
                        ):

                            report.status = (
                                "failed"
                            )

                            return report

            if not success:

                report.status = "failed"

                return report

        if report.failed:

            report.status = "failed"

        elif self.graph_engine.is_complete(
            graph
        ):

            report.status = "completed"

        else:

            report.status = "incomplete"

        return report
