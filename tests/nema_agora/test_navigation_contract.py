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
    assert "from nema_agora.workflow import ALLOWED_TRANSITIONS, apply_status_update" in page
    assert "status in ALLOWED_TRANSITIONS[selected[\"status\"]]" in page


def test_evidence_reload_invalidates_old_bundle_and_export_before_store_call():
    page = (
        Path(__file__).resolve().parents[2] / "pages" / "18_NEMA_AGORA.py"
    ).read_text(encoding="utf-8")
    button = page.index('"Prepare / reload evidence case"')
    clear_bundle = page.index('st.session_state.pop(f"evidence_bundle_{selected_id}", None)', button)
    clear_export = page.index('st.session_state.pop(f"evidence_export_{selected_id}", None)', clear_bundle)
    store_call = page.index("service.build_governed_evidence_case(selected_id, principal)", clear_export)
    assert button < clear_bundle < clear_export < store_call


def test_advisory_analysis_has_user_safe_failure_handling():
    page = (
        Path(__file__).resolve().parents[2] / "pages" / "18_NEMA_AGORA.py"
    ).read_text(encoding="utf-8")
    action = page.index('st.button("Run advisory analysis"')
    handler = page.index("except Exception as exc:", action)
    safe_message = page.index(
        "Advisory analysis could not be completed. No case status or observation data was changed.",
        handler,
    )
    assert action < handler < safe_message


def test_copilot_and_shadow_retries_clear_stale_results_before_execution():
    page = (
        Path(__file__).resolve().parents[2] / "pages" / "18_NEMA_AGORA.py"
    ).read_text(encoding="utf-8")
    copilot = page.index('st.button("Prepare reviewer brief"')
    copilot_clear = page.index('st.session_state.pop("nema_agora_copilot_brief", None)', copilot)
    copilot_run = page.index("service.build_reviewer_copilot(", copilot_clear)
    shadow = page.index('st.button("Run isolated shadow analysis"')
    shadow_clear = page.index('st.session_state.pop("nema_agora_shadow_result", None)', shadow)
    shadow_run = page.index("service.run_shadow(selected_shadow, principal)", shadow_clear)
    assert copilot < copilot_clear < copilot_run
    assert shadow < shadow_clear < shadow_run
