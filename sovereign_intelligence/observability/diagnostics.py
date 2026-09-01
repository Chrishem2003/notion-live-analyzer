from __future__ import annotations

from .run_models import IntelligenceRun
from .run_recorder import RunRecorder


class RunDiagnostics:

    def __init__(
        self,
        recorder: RunRecorder | None = None,
    ):

        self.recorder = (
            recorder
            or RunRecorder()
        )

    def start(
        self,
        metadata=None,
    ) -> IntelligenceRun:

        run = IntelligenceRun(
            metadata=metadata or {}
        )

        run.add_event(
            "run_started",
            "started",
        )

        return run

    def succeed(
        self,
        run: IntelligenceRun,
        data=None,
    ):

        run.add_event(
            "run_completed",
            "completed",
            data,
        )

        run.complete(
            "completed"
        )

        self.recorder.record(run)

        return run

    def fail(
        self,
        run: IntelligenceRun,
        error: str,
    ):

        run.add_event(
            "run_failed",
            "failed",
            {
                "error": error
            },
        )

        run.complete(
            "failed",
            error,
        )

        self.recorder.record(run)

        return run
