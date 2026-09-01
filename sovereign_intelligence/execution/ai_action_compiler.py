from __future__ import annotations

from .ai_plan import AIActionProposal
from .autonomous_models import Action
from .ai_action_validator import (
    AIActionValidator,
)


class AIActionCompiler:

    def __init__(
        self,
        validator: AIActionValidator,
    ):

        self.validator = validator

    def compile(
        self,
        proposal: AIActionProposal,
    ) -> Action:

        decision = self.validator.validate(
            proposal
        )

        if not decision.allowed:

            raise PermissionError(
                decision.reason
            )

        return Action(
            kind=proposal.action,
            target=proposal.target,
            arguments=dict(
                proposal.arguments
            ),
            reason=proposal.rationale,
        )
