"""
modules/task_client.py â€” Streamlit <-> Celery bridge.

Streamlit re-runs the whole script on every interaction, so "polling" here
means: submit once, stash the task id in session_state, and on each rerun
check the result backend and redraw a progress bar until it's done. No
blocking calls, no threads inside the Streamlit process.

Usage from any hub page:

    from modules.task_client import submit_task, render_task_progress

    if st.button("Harvest 500 papers"):
        submit_task("lit_harvest", "tasks.harvest_literature_task",
                    args=(query, 500, contact_email, sort_by))

    result = render_task_progress("lit_harvest")
    if result is not None:
        df = pd.DataFrame(result["records"])
        st.dataframe(df)
"""

import streamlit as st
from celery.result import AsyncResult
from celery_app import celery_app


def submit_task(session_key: str, task_name: str, args: tuple = (), kwargs: dict = None):
    """Fire a task and remember its id under `session_key` in session_state."""
    async_result = celery_app.send_task(task_name, args=args, kwargs=kwargs or {})
    st.session_state[f"_task_id__{session_key}"] = async_result.id
    st.session_state[f"_task_done__{session_key}"] = False
    return async_result.id


def get_task_status(session_key: str):
    """Return (state, meta) for the job stored under `session_key`, or None if none submitted."""
    task_id = st.session_state.get(f"_task_id__{session_key}")
    if not task_id:
        return None, None
    result = AsyncResult(task_id, app=celery_app)
    return result.state, (result.info if isinstance(result.info, dict) else {})


def render_task_progress(session_key: str, poll_seconds: float = 1.5):
    """
    Render a live progress bar for the job under `session_key`. Returns the
    task's return value once it's finished (SUCCESS), or None while it's
    still running / hasn't been submitted / failed.

    Call this on every rerun (it self-triggers reruns via st.rerun while a
    job is in flight â€” no external polling loop needed).
    """
    task_id = st.session_state.get(f"_task_id__{session_key}")
    if not task_id:
        return None

    if st.session_state.get(f"_task_done__{session_key}"):
        # Already finished on a prior rerun â€” don't re-poll, just return the cached value.
        return st.session_state.get(f"_task_result__{session_key}")

    result = AsyncResult(task_id, app=celery_app)
    state = result.state
    meta = result.info if isinstance(result.info, dict) else {}

    progress_box = st.empty()

    if state in ("PENDING",):
        progress_box.info("â³ Job queued â€” waiting for a worker to pick it up...")
        time_delay(poll_seconds)
        st.rerun()

    elif state == "PROGRESS":
        current = meta.get("current", 0)
        total = meta.get("total", 1) or 1
        stage = meta.get("stage", "working...")
        with progress_box.container():
            st.progress(min(current / total, 1.0))
            st.caption(f"ðŸ”„ {stage}")
        time_delay(poll_seconds)
        st.rerun()

    elif state == "SUCCESS":
        progress_box.success("âœ… Job complete.")
        value = result.result
        st.session_state[f"_task_done__{session_key}"] = True
        st.session_state[f"_task_result__{session_key}"] = value
        return value

    elif state == "FAILURE":
        error_msg = meta.get("error", str(result.result))
        progress_box.error(f"âŒ Job failed: {error_msg}")
        st.session_state[f"_task_done__{session_key}"] = True
        st.session_state[f"_task_result__{session_key}"] = None
        return None

    else:
        progress_box.info(f"Status: {state}")
        time_delay(poll_seconds)
        st.rerun()

    return None


def time_delay(seconds: float):
    """Isolated so tests can monkeypatch it instead of actually sleeping."""
    import time
    time.sleep(seconds)


def cancel_task(session_key: str):
    """Revoke a running job and clear it from session_state."""
    task_id = st.session_state.get(f"_task_id__{session_key}")
    if task_id:
        celery_app.control.revoke(task_id, terminate=True)
    for suffix in ("_task_id__", "_task_done__", "_task_result__"):
        st.session_state.pop(f"{suffix}{session_key}", None)
