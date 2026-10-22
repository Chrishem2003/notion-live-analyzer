"""Guard automation screens against claiming execution without evidence."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_scheduler_inventory_does_not_claim_jobs_are_running():
    source = (ROOT / "workflow_scheduler.py").read_text(encoding="utf-8")
    assert "PLANNED — NOT RUNNING" in source
    assert "No execution evidence" in source
    assert "No background task was started." in source
    assert '"Status": "ACTIVE"' not in source
    assert '"Status": "RUNNING"' not in source
    assert "Zero Failures" not in source
    assert "Daemon Active" not in source


def test_master_automation_never_marks_preview_request_as_success():
    source = (ROOT / "master_automation.py").read_text(encoding="utf-8")
    assert "PREVIEW_ONLY_NOT_EXECUTED" in source
    assert "No workflow was executed." in source
    assert "execution adapter is not connected" in source.lower()
    assert '"SUCCESS"' not in source
    assert "successfully executed" not in source.lower()
    assert "chief.investigator@lab.org" not in source
