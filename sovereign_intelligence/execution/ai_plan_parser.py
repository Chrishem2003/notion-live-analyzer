from __future__ import annotations

import json
from typing import Any

from .ai_plan import (
    AIActionProposal,
    AIPlanProposal,
)


class AIPlanParser:

    def parse(
        self,
        payload: str | dict[str, Any],
    ) -> AIPlanProposal:

        if isinstance(payload, str):

            try:

                data = json.loads(payload)

            except json.JSONDecodeError as exc:

                raise ValueError(
                    "AI plan is not valid JSON."
                ) from exc

        else:

            data = payload

        if not isinstance(data, dict):

            raise ValueError(
                "AI plan must be an object."
            )

        objective = str(
            data.get("objective", "")
        ).strip()

        if not objective:

            raise ValueError(
                "AI plan objective is required."
            )

        raw_actions = data.get(
            "actions",
            [],
        )

        if not isinstance(
            raw_actions,
            list,
        ):

            raise ValueError(
                "AI plan actions must be a list."
            )

        actions = []

        for item in raw_actions:

            if not isinstance(
                item,
                dict,
            ):

                raise ValueError(
                    "Each AI action must be an object."
                )

            action = str(
                item.get("action", "")
            ).strip()

            target = str(
                item.get("target", "")
            ).strip()

            arguments = item.get(
                "arguments",
                {},
            )

            if not action:

                raise ValueError(
                    "AI action is missing action type."
                )

            if not target:

                raise ValueError(
                    "AI action is missing target."
                )

            if not isinstance(
                arguments,
                dict,
            ):

                raise ValueError(
                    "AI action arguments must be an object."
                )

            actions.append(
                AIActionProposal(
                    action=action,
                    target=target,
                    arguments=arguments,
                    rationale=str(
                        item.get(
                            "rationale",
                            "",
                        )
                    ),
                )
            )

        confidence = float(
            data.get(
                "confidence",
                0.0,
            )
        )

        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        return AIPlanProposal(
            objective=objective,
            actions=actions,
            final_response=str(
                data.get(
                    "final_response",
                    "",
                )
            ),
            confidence=confidence,
            metadata=data.get(
                "metadata",
                {},
            )
            if isinstance(
                data.get(
                    "metadata",
                    {},
                ),
                dict,
            )
            else {},
        )


def parse_ai_plan(
    payload: str | dict[str, Any],
) -> AIPlanProposal:

    return AIPlanParser().parse(
        payload
    )
