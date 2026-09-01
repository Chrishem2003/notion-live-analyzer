from __future__ import annotations

import json

from ..models import AIRequest
from .ai_plan import AIPlanProposal
from .ai_plan_parser import AIPlanParser


class ProviderPlanningAdapter:

    def __init__(
        self,
        provider,
        parser: AIPlanParser | None = None,
    ):

        self.provider = provider
        self.parser = parser or AIPlanParser()

    def build_request(
        self,
        objective: str,
        available_tools: list[str],
        context: str = "",
    ) -> AIRequest:

        tools = ", ".join(
            available_tools
        ) or "none"

        system = f"""
You are the planning component of Sovereign Intelligence.

Your task is to analyze the user's objective and produce a
STRUCTURED execution plan.

Available controlled tools:
{tools}

You MUST return JSON only.

Required JSON structure:

{{
  "objective": "string",
  "actions": [
    {{
      "action": "tool",
      "target": "tool_name",
      "arguments": {{}},
      "rationale": "string"
    }}
  ],
  "final_response": "string",
  "confidence": 0.0
}}

Rules:

1. Never invent unavailable tools.
2. Never request shell commands.
3. Never request arbitrary code execution.
4. Use only the supplied tools.
5. Keep arguments structured.
6. Do not claim an action was executed.
7. Separate planning from execution.
8. If the objective cannot be safely executed, return an empty
   action list and explain why in final_response.
9. Confidence must be between 0 and 1.
10. Return valid JSON and nothing else.

Context:

{context[:12000]}
"""

        return AIRequest(
            prompt=objective,
            system=system,
            temperature=0.0,
            max_tokens=4096,
        )

    def generate_plan(
        self,
        objective: str,
        available_tools: list[str],
        context: str = "",
    ) -> AIPlanProposal:

        request = self.build_request(
            objective=objective,
            available_tools=available_tools,
            context=context,
        )

        response = self.provider.generate(
            request
        )

        return self.parser.parse(
            response.text
        )
