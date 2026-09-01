from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .autonomous_models import (
    Action,
    AutonomousState,
)


@dataclass
class Decision:

    action: Action | None

    reason: str

    finished: bool = False


class AdaptivePlanner:

    def __init__(
        self,
        decider: Callable[
            [AutonomousState],
            Decision
        ] | None = None,
    ):

        self.decider = decider

    def decide(
        self,
        state: AutonomousState,
    ) -> Decision:

        if self.decider is not None:

            return self.decider(
                state
            )

        if not state.completed_actions:

            return Decision(
                action=Action(
                    kind="tool",
                    target="calculator",
                    arguments={
                        "expression": "1+1"
                    },
                    reason=(
                        "Default diagnostic "
                        "action."
                    ),
                ),
                reason=(
                    "No previous action exists; "
                    "performing a controlled "
                    "diagnostic action."
                ),
            )

        return Decision(
            action=None,
            reason=(
                "No additional action "
                "was selected."
            ),
            finished=True,
        )
