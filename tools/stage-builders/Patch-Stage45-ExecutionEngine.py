from pathlib import Path

path = Path(r".\sovereign_intelligence\execution\orchestrator.py")
text = path.read_text(encoding="utf-8")

old = '''    def execute(
        self,
        problem: Problem,
        plan: Plan,
        provider_name: str,
        model: str,
        memory_context: str = "",
        evidence_context: str = "",
    ) -> BrainResult:
'''

new = '''    def execute(
        self,
        problem: Problem,
        plan: Plan,
        provider_name: str,
        model: str,
        memory_context: str = "",
        evidence_context: str = "",
        strategy: str = "direct",
        route: str = "standard_execution",
    ) -> BrainResult:
'''

if old not in text:
    raise SystemExit("Expected execute signature not found.")

text = text.replace(old, new, 1)

marker = '''        system = f"""
You are Sovereign Intelligence, the
problem-solving engine of a larger
software platform.
'''

replacement = '''        strategy_modes = {
            "direct": (
                "Use a direct, efficient problem-solving approach. "
                "Prioritize correctness and actionable output."
            ),
            "deep": (
                "Use a deep-reasoning approach. "
                "Break difficult problems into explicit subproblems, "
                "test assumptions, consider alternatives, and resolve "
                "important edge cases before producing the answer."
            ),
            "verify": (
                "Use a verification-first approach. "
                "Challenge important claims, identify possible errors, "
                "and prefer conclusions supported by evidence."
            ),
            "research": (
                "Use a research-oriented approach. "
                "Prioritize evidence, distinguish known information "
                "from assumptions, and identify missing evidence."
            ),
            "analysis": (
                "Use an analytical approach. "
                "Decompose the problem, compare relevant factors, "
                "identify relationships, and derive a defensible conclusion."
            ),
            "debug": (
                "Use a debugging approach. "
                "Identify likely failure points, trace the relevant "
                "execution path, isolate root causes, and propose "
                "specific corrective actions."
            ),
            "plan": (
                "Use a planning approach. "
                "Convert the objective into an ordered, dependency-aware "
                "set of actionable steps and identify risks or blockers."
            ),
        }

        selected_strategy = str(strategy or "direct").strip().lower()
        selected_route = str(route or "standard_execution").strip()

        strategy_instruction = strategy_modes.get(
            selected_strategy,
            strategy_modes["direct"],
        )

        system = f"""
You are Sovereign Intelligence, the
problem-solving engine of a larger
software platform.

Adaptive execution mode:
Strategy: {selected_strategy}
Route: {selected_route}

Strategy-specific operating mode:
{strategy_instruction}
'''

if marker not in text:
    raise SystemExit("Expected system prompt marker not found.")

text = text.replace(marker, replacement, 1)

old_trace = '''        trace.append(
            {
                "event": "provider_request",
                "provider": provider_name,
                "model": model,
                "evidence_attached": bool(
                    evidence_context.strip()
                ),
            }
        )
'''

new_trace = '''        trace.append(
            {
                "event": "provider_request",
                "provider": provider_name,
                "model": model,
                "strategy": selected_strategy,
                "route": selected_route,
                "evidence_attached": bool(
                    evidence_context.strip()
                ),
            }
        )
'''

if old_trace not in text:
    raise SystemExit("Expected provider trace block not found.")

text = text.replace(old_trace, new_trace, 1)

path.write_text(text, encoding="utf-8")

print("EXECUTION_ENGINE_STAGE45_PATCH_OK")
