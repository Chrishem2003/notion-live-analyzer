"""Regression tests for truthful scheduler state and fail-closed controls."""
from __future__ import annotations

import pandas as pd
import pytest

import workflow_scheduler as root_scheduler
from modules import workflow_scheduler as module_scheduler


@pytest.mark.parametrize("scheduler", [root_scheduler, module_scheduler])
def test_unconfigured_scheduler_returns_no_fabricated_jobs(scheduler):
    frame = scheduler.get_scheduled_workflows()

    assert isinstance(frame, pd.DataFrame)
    assert frame.empty
    assert list(frame.columns) == scheduler.WORKFLOW_COLUMNS


class _Column:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


@pytest.mark.parametrize("scheduler", [root_scheduler, module_scheduler])
def test_scheduler_actions_stay_disabled_until_executor_exists(monkeypatch, scheduler):
    import streamlit as st

    monkeypatch.setattr(st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "columns", lambda count, *args, **kwargs: [_Column() for _ in range(count)])
    calls = []

    def button(label, *args, **kwargs):
        calls.append((label, kwargs.get("disabled", False)))
        return False

    monkeypatch.setattr(st, "button", button)
    scheduler.render_workflow_scheduler_panel()

    assert len(calls) == 2
    assert all(disabled for _, disabled in calls)
