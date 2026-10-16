"""Regression tests for composing optional audit-portal submission filters."""
from __future__ import annotations

import pytest

from modules.audit_portal import CHRISHEMSubmissionSystem


@pytest.fixture
def portal(tmp_path):
    system = CHRISHEMSubmissionSystem(tmp_path / "portal.sqlite3")
    rows = [
        (1, "Alice", "A1", "submitted", 10.0),
        (1, "Bob", "B1", "submitted", 20.0),
        (2, "Alice", "A2", "reviewed", 30.0),
        (1, "Alice", "A3", "reviewed", 40.0),
        (2, "Casey", "C1", "returned", 50.0),
    ]
    with system._get_conn() as conn:
        conn.executemany(
            """INSERT INTO portal_submissions
               (project_id, student_name, title, encrypted_content, status, submitted_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [(project, student, title, "fixture-ciphertext", status, ts)
             for project, student, title, status, ts in rows],
        )
        conn.commit()
    return system


def titles(rows):
    return {row["title"] for row in rows}


def test_no_filters_returns_all_rows(portal):
    assert len(portal.get_submissions()) == 5


def test_each_optional_filter_works_independently(portal):
    assert titles(portal.get_submissions(project_id=1)) == {"A1", "B1", "A3"}
    assert titles(portal.get_submissions(student_name="Alice")) == {"A1", "A2", "A3"}
    assert titles(portal.get_submissions(status="reviewed")) == {"A2", "A3"}


def test_all_filters_compose_as_and_conditions(portal):
    rows = portal.get_submissions(project_id=1, student_name="Alice", status="reviewed")
    assert titles(rows) == {"A3"}


def test_filter_values_remain_parameterized(portal):
    rows = portal.get_submissions(student_name="Alice' OR 1=1 --")
    assert rows == []
