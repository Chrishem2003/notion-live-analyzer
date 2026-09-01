from __future__ import annotations

from dataclasses import dataclass

from .ai_plan import AIActionProposal


@dataclass(frozen=True)
class ActionValidation:

    allowed: bool

    reason: str


class AIActionValidator:

    def __init__(
        self,
        allowed_actions=None,
        allowed_targets=None,
    ):

        self.allowed_actions = set(
            allowed_actions
            or {
                "tool",
            }
        )

        self.allowed_targets = (
            set(allowed_targets)
            if allowed_targets is not None
            else None
        )

    def validate(
        self,
        action: AIActionProposal,
    ) -> ActionValidation:

        if action.action not in self.allowed_actions:

            return ActionValidation(
                False,
                (
                    "Action type is not "
                    "permitted."
                ),
            )

        if (
            self.allowed_targets is not None
            and action.target
            not in self.allowed_targets
        ):

            return ActionValidation(
                False,
                (
                    "Action target is not "
                    "permitted."
                ),
            )

        if not isinstance(
            action.arguments,
            dict,
        ):

            return ActionValidation(
                False,
                "Action arguments must be an object.",
            )

        return ActionValidation(
            True,
            "Action permitted.",
        )

    def validate_plan(
        self,
        actions,
    ):

        return [
            self.validate(action)
            for action in actions
        ]
