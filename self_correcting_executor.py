"""
self_correcting_executor.py
Automated Schema Self-Correction Engine.

Wraps the data-analysis agent so that when pandas/SQL/numpy code raises an
exception, the stack trace is fed back to the LLM (via modules.llm_router),
which proposes a corrected code snippet. The executor retries up to
`max_retries` times with the corrected code.

Flow:
  run_code(code, context) -> try execute
    on error -> capture traceback -> LLM fix -> sanitize -> retry
    else -> return result + execution log
"""
from __future__ import annotations

import io
import traceback
from contextlib import redirect_stdout
from typing import Any, Callable, Dict, List, Optional

try:
    from modules.llm_router import get_router

    _router = get_router()
except Exception:
    _router = None


class SelfCorrectingExecutor:
    """Executes analysis code blocks with automated LLM-driven self-correction."""

    def __init__(self, max_retries: int = 3, router=None):
        self.max_retries = max_retries
        self._router = router or _router

    # ------------------------------------------------------------------
    def _sanitize(self, code: str) -> str:
        """Strip markdown fences / non-code decorations from LLM output."""
        code = code.strip()
        if code.startswith("```"):
            lines = code.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            code = "\n".join(lines)
        return code.strip()

    def _ask_llm_for_fix(self, original_code: str, error: str) -> Optional[str]:
        if self._router is None:
            return None
        prompt = (
            "The following Python analysis code raised an exception. "
            "Fix ONLY the bug and return the corrected full code block. No commentary.\n\n"
            f"### Original code:\n{original_code}}\n\n"
            f"### Exception traceback:\n{error}}"
        )
        try:
            fixed = self._router.generate(prompt, task="general", temperature=0.1)
            fixed = self._sanitize(fixed)
            return fixed if fixed and fixed != original_code else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    def run_code(
        self,
        code: str,
        globals_dict: Optional[Dict[str, Any]] = None,
        max_retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute `code` in a fresh namespace, self-correcting on failure.
        Returns {success, output, result_vars, attempts, log}.
        """
        retries = max_retries or self.max_retries
        namespace = {"__name__": "__main__"}
        if globals_dict:
            namespace.update(globals_dict)

        stream = io.StringIO()
        log: List[Dict[str, Any]] = []
        current_code = code

        for attempt in range(1, retries + 2):
            namespace_attempt = dict(namespace)
            try:
                with redirect_stdout(stream):
                    exec(compile(current_code, "<self_correcting_executor>", "exec"), namespace_attempt)
                # Collect non-builtin result vars
                result_vars = {
                    k: repr(v)[:300]
                    for k, v in namespace_attempt.items()
                    if not k.startswith("__") and callable(v) is False and not isinstance(v, (type, bytes))
                }
                log.append({"attempt": attempt, "status": "success", "code": current_code})
                return {
                    "success": True,
                    "output": stream.getvalue(),
                    "result_vars": result_vars,
                    "attempts": attempt,
                    "log": log,
                }
            except Exception as exc:  # noqa: BLE001
                tb = traceback.format_exc()
                log.append({"attempt": attempt, "status": "error", "error": str(exc), "code": current_code})
                if attempt > retries:
                    return {
                        "success": False,
                        "output": stream.getvalue(),
                        "error": str(exc),
                        "traceback": tb,
                        "attempts": attempt,
                        "log": log,
                    }
                fixed = self._ask_llm_for_fix(current_code, tb)
                if not fixed:
                    return {
                        "success": False,
                        "output": stream.getvalue(),
                        "error": str(exc),
                        "traceback": tb,
                        "attempts": attempt,
                        "log": log,
                    }
                current_code = fixed
        return {"success": False, "attempts": retries + 1, "log": log}

    # ------------------------------------------------------------------
    def run_function(self, fn: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Run a Python callable with a try/except self-correction wrapper."""
        try:
            result = fn(*args, **kwargs)
            return {"success": True, "result": result}
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            return {"success": False, "error": str(exc), "traceback": tb}


# Singleton
_executor_instance: Optional[SelfCorrectingExecutor] = None


def get_executor() -> SelfCorrectingExecutor:
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = SelfCorrectingExecutor()
    return _executor_instance


def safe_execute(code: str, globals_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Public convenience wrapper."""
    return get_executor().run_code(code, globals_dict)

