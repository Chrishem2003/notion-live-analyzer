from __future__ import annotations

from ..base import Tool
from ..permissions import ToolPermissions

from .calculator import calculate


class CalculatorTool(Tool):

    name = "calculator"

    description = (
        "Safely evaluate a mathematical "
        "expression using a restricted "
        "numeric expression evaluator."
    )

    permissions = ToolPermissions(
        read=False,
        write=False,
        execute=False,
        network=False,
        destructive=False,
    )

    def execute(
        self,
        expression: str,
        **kwargs,
    ):

        return {
            "expression": expression,
            "result": calculate(
                expression
            ),
        }
