"""Navigation contract tests: one visible NEMA-AGORA destination only."""
from pathlib import Path

from app_navigation import discover_other_pages


def test_nema_specialist_pages_are_not_exposed_as_separate_sidebar_entries(tmp_path):
    root = tmp_path
    pages = root / "pages"
    pages.mkdir()
    for name in (
        "18_NEMA_AGORA.py",
        "19_NEMA_AGORA_ADMIN.py",
        "24_NEMA_AGORA_CONTROLLED_SHADOW.py",
        "01_Statistics_Studio.py",
        "16_Career_OS.py",
    ):
        (pages / name).write_text("# navigation fixture\n", encoding="utf-8")

    visible = discover_other_pages(root, pages)

    assert visible == [
        ("pages/01_Statistics_Studio.py", "Statistics Studio"),
        ("pages/16_Career_OS.py", "Career OS"),
    ]
    assert all("NEMA_AGORA" not in path for path, _ in visible)


def test_missing_pages_directory_is_safe(tmp_path):
    assert discover_other_pages(tmp_path, tmp_path / "missing") == []


def test_single_page_case_management_exposes_explicit_workflow_run_action():
    page = (
        Path(__file__).resolve().parents[2] / "pages" / "18_NEMA_AGORA.py"
    ).read_text(encoding="utf-8")

    assert 'st.form_submit_button("Run workflow transition"' in page
    assert "Workflow run: choose the next case status" in page
    assert "Only authorised reviewers can run this step" in page
