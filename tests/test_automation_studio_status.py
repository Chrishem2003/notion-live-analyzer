"""Regression checks for truthful Automation Studio status messaging."""
from pathlib import Path


def test_embed_status_does_not_claim_workflow_health():
    page = (Path(__file__).resolve().parents[1] / "pages" / "17_Automation_Studio.py").read_text(encoding="utf-8-sig")
    assert "Embed reachable" in page
    assert "does not verify workflow execution" in page
    assert 'st.success(f"Online · {latency_ms} ms")' not in page


def test_local_notes_disclose_non_durable_hosted_storage():
    page = (Path(__file__).resolve().parents[1] / "pages" / "17_Automation_Studio.py").read_text(encoding="utf-8-sig")
    assert "may disappear after a restart or redeploy" in page
    assert "Do not store passwords, API keys" in page
    assert "Persistence across restarts/redeploys is not guaranteed" in page
