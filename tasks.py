"""
tasks.py
Asynchronous Task Runner & Queue for the Multi-Problem Solver.

Architecture:
  - Primary broker: Celery + Redis (production).
  - Automatic fallback: in-process ThreadPoolExecutor when Redis/Celery are
    unavailable (e.g., local VSCode runs). This guarantees the UI never hangs.
  - All task state is persisted through modules/task_status_registry.py so the
    Streamlit frontend can poll live progress via task IDs.

Usage:
    from tasks import dispatch_task, get_task_status
    task_id = dispatch_task("research_papers", query="bioinformatics", limit=50)
    status  = get_task_status(task_id)   # -> dict with progress / result
"""
from __future__ import annotations

import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

from modules.task_status_registry import (
    create_task,
    get_task,
    mark_done,
    mark_failed,
    update_task,
)

# ---------------------------------------------------------------------------
# Celery + Redis (optional)
# ---------------------------------------------------------------------------
try:
    from celery import Celery

    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    celery_app = Celery("multi_problem_solver", broker=REDIS_URL, backend=REDIS_URL)
    celery_app.conf.task_track_started = True
    HAS_CELERY = True
except Exception:  # pragma: no cover - Redis/Celery not installed
    celery_app = None
    HAS_CELERY = False

# ---------------------------------------------------------------------------
# ThreadPool fallback executor
# ---------------------------------------------------------------------------
_executor = ThreadPoolExecutor(max_workers=max(2, (os.cpu_count() or 2) - 1))
_REGISTRY: Dict[str, Callable] = {}
_HANDLER_LOCK = object()


def register_task_handler(name: str, fn: Callable) -> None:
    """Register a named, callable task handler."""
    _REGISTRY[name] = fn


def _run_registered(name: str, task_id: str, **kwargs) -> Any:
    """Execute a registered handler inside a worker and mirror progress."""
    fn = _REGISTRY.get(name)
    if fn is None:
        raise ValueError(f"Unknown task handler: {name}}")

    def progress_cb(progress: float, message: str = "") -> None:
        update_task(task_id, progress=progress, message=message)

    try:
        update_task(task_id, status="RUNNING", progress=1.0, message="Task started")
        # Provide a progress callback + task_id to handlers that accept them.
        result = fn(progress_cb=progress_cb, task_id=task_id, **kwargs)
        mark_done(task_id, result, message="Completed successfully")
        return result
    except Exception as exc:  # noqa: BLE001
        mark_failed(task_id, f"{exc}}\n{traceback.format_exc()}}")
        raise


dispatch_counter = {"n": 0}


def dispatch_task(name: str, **kwargs) -> Dict[str, Any]:
    """
    Dispatch a named task asynchronously. Returns the task's status dict.
    Uses Celery if available, otherwise the ThreadPool fallback.
    """
    task_id = create_task(name=name, meta={"handler": name, **kwargs})

    if HAS_CELERY and os.environ.get("CELERY_MODE", "0") == "1":
        # Production path: submit to Redis-backed Celery broker.
        try:
            celery_app.send_task(
                "multi_problem_solver.run_task",
                args=[name, task_id],
                kwargs=kwargs,
                task_id=task_id,
            )
            return get_task(task_id) or {"id": task_id, "status": "PENDING"}
        except Exception:
            # Fall through to thread pool if broker unreachable.
            pass

    # Local / VSCode path: in-process thread pool (never blocks the UI).
    if name in _REGISTRY:
        _executor.submit(_run_registered, name, task_id, **kwargs)
    else:
        mark_failed(task_id, f"Unknown task handler: {name}}")
    return get_task(task_id) or {"id": task_id, "status": "PENDING"}


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Return live status for a task ID."""
    return get_task(task_id)


# ---------------------------------------------------------------------------
# Built-in example task handlers (production-grade reference implementations)
# ---------------------------------------------------------------------------

def _echo_handler(progress_cb=None, task_id=None, message: str = "hello", **kwargs):
    total = 10
    for i in range(total):
        time.sleep(0.1)
        if progress_cb:
            progress_cb((i + 1) / total * 100, f"Echoing: {message}} ({i + 1}}/{total}})")
    return {"echo": message, "received": bool(kwargs)}


def _sample_pipeline_handler(
    progress_cb=None,
    task_id=None,
    steps: int = 5,
    label: str = "pipeline",
    **kwargs,
):
    """Simulates a heavy multi-step pipeline (literature pull, data audit, synthesis)."""
    outputs = []
    for i in range(steps):
        time.sleep(0.2)
        outputs.append(f"step-{i + 1}}")
        if progress_cb:
            progress_cb((i + 1) / steps * 100, f"{label}}: executed step {i + 1}}/{steps}}")
    return {"pipeline": label, "steps": outputs, "total_steps": steps}


# Register built-in handlers
register_task_handler("echo", _echo_handler)
register_task_handler("sample_pipeline", _sample_pipeline_handler)


def register_default_handlers() -> None:
    """Idempotent hook called by the FastAPI app & Streamlit at startup."""
    # Ensure agents.py / rag_engine.py handlers are registered when available.
    try:
        from agents import register_agents_task_handlers

        register_agents_task_handlers()
    except Exception:
        pass
    try:
        from rag_engine import register_rag_task_handlers

        register_rag_task_handlers()
    except Exception:
        pass

