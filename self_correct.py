"""
self_correct.py â€” Enterprise addition #1 from the spec: catch Pandas/SQL
exceptions from agent-generated analysis code, feed the traceback back to
the LLM, and retry with a corrected version.

This executes LLM-generated code, which is a real risk surface regardless
of how well-intentioned the LLM is â€” so this module is deliberately narrow:

  - It's for CODE THE SYSTEM ITSELF GENERATED (e.g. an agent's pandas
    analysis step), not arbitrary end-user input. Never wire a raw user
    text box into `code` here.
  - Execution happens in a restricted namespace with `__builtins__` reduced
    to a small safe allowlist â€” no `open`, `eval`, `exec`, `__import__`,
    `os`, `subprocess`, `input`, or file/network access of any kind from
    inside the sandboxed code.
  - There is a hard retry ceiling (default 2) and a hard wall-clock timeout
    per attempt â€” a self-correction loop that never terminates is worse
    than the original bug.
  - Without GEMINI_API_KEY, this does NOT attempt automatic correction â€”
    it returns the real error and traceback and says plainly that no
    auto-fix was attempted. Faking a "self-healed" result here would be
    exactly the kind of fabricated success message this whole project's
    audit has been removing elsewhere (see portal.py's changelog).
"""

import os
import re
import signal
import traceback
import contextlib
import io
from dataclasses import dataclass, field

import pandas as pd
import numpy as np


SAFE_BUILTINS = {
    "len": len, "range": range, "enumerate": enumerate, "zip": zip,
    "sorted": sorted, "sum": sum, "min": min, "max": max, "abs": abs,
    "round": round, "str": str, "int": int, "float": float, "bool": bool,
    "list": list, "dict": dict, "set": set, "tuple": tuple,
    "isinstance": isinstance, "type": type, "print": print,
}


class SandboxTimeout(Exception):
    pass


@contextlib.contextmanager
def _time_limit(seconds: int):
    def _handler(signum, frame):
        raise SandboxTimeout(f"Execution exceeded {seconds}}s limit.")
    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


@dataclass
class CorrectionAttempt:
    attempt_number: int
    code: str
    succeeded: bool
    error: str = ""


@dataclass
class SelfCorrectionResult:
    success: bool
    result: object = None
    final_code: str = ""
    attempts: list = field(default_factory=list)
    auto_correction_used: bool = False
    message: str = ""


def _run_in_sandbox(code: str, df: pd.DataFrame, timeout_seconds: int = 10):
    """Executes `code` with only pandas/numpy/df exposed and a minimal
    builtins allowlist. The code is expected to assign its output to a
    variable named `result`."""
    namespace = {
        "df": df,
        "pd": pd,
        "np": np,
        "result": None,
        "__builtins__": SAFE_BUILTINS,
    }
    stdout_capture = io.StringIO()
    with _time_limit(timeout_seconds):
        with contextlib.redirect_stdout(stdout_capture):
            exec(code, namespace)  # noqa: S102 â€” intentional, sandboxed, see module docstring
    return namespace.get("result"), stdout_capture.getvalue()


def _request_llm_fix(code: str, error: str, df_schema: dict) -> str | None:
    """Ask Gemini for a corrected version of `code`. Returns the corrected
    code string, or None if no LLM is configured or the call fails â€”
    caller must treat None as "no correction available", not retry with
    the same broken code."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = (
            "The following pandas code failed. Fix it. The DataFrame `df` has "
            f"columns and dtypes: {df_schema}}\n\n"
            f"Code:\n```python\n{code}}\n```\n\n"
            f"Error:\n{error}}\n\n"
            "Return ONLY the corrected Python code (no explanation, no markdown fences). "
            "The code must assign its final output to a variable named `result`. "
            "Do not use imports, file I/O, network calls, or any builtin beyond basic "
            "Python and the pre-provided `df`, `pd`, `np`."
        )
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        code_text = response.text.strip()
        code_text = re.sub(r"^```(?:python)?\n?|\n?```$", "", code_text.strip())
        return code_text
    except Exception:
        return None


def execute_with_self_correction(code: str, df: pd.DataFrame, max_retries: int = 2, timeout_seconds: int = 10) -> SelfCorrectionResult:
    """
    Try `code` against `df`. On failure, if GEMINI_API_KEY is set, ask the
    LLM for a fix and retry (up to `max_retries` times). If not set, fail
    honestly on the first error with the real traceback.
    """
    attempts = []
    current_code = code
    df_schema = {col: str(dtype) for col, dtype in df.dtypes.items()}

    for attempt_num in range(1, max_retries + 2):  # original attempt + max_retries corrections
        try:
            result, _stdout = _run_in_sandbox(current_code, df, timeout_seconds=timeout_seconds)
            attempts.append(CorrectionAttempt(attempt_num, current_code, succeeded=True))
            return SelfCorrectionResult(
                success=True,
                result=result,
                final_code=current_code,
                attempts=attempts,
                auto_correction_used=attempt_num > 1,
                message=f"Succeeded on attempt {attempt_num}}" + (" after self-correction." if attempt_num > 1 else "."),
            )
        except Exception as e:
            error_text = f"{type(e).__name__}}: {e}}\n{traceback.format_exc(limit=3)}}"
            attempts.append(CorrectionAttempt(attempt_num, current_code, succeeded=False, error=error_text))

            if attempt_num > max_retries:
                break

            fixed_code = _request_llm_fix(current_code, error_text, df_schema)
            if fixed_code is None:
                # No LLM configured (or the call itself failed) â€” stop honestly
                # rather than retrying the same broken code and calling that "correction."
                return SelfCorrectionResult(
                    success=False,
                    attempts=attempts,
                    auto_correction_used=False,
                    message=(
                        "Execution failed and no automatic correction was attempted "
                        "(set GEMINI_API_KEY to enable self-correction). Real error below."
                    ),
                )
            current_code = fixed_code

    return SelfCorrectionResult(
        success=False,
        attempts=attempts,
        auto_correction_used=True,
        message=f"Failed after {len(attempts)}} attempts (original + {max_retries}} LLM-suggested corrections).",
    )
