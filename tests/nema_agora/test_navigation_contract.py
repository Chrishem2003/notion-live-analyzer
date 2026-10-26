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


def test_governed_evidence_storage_failures_are_user_safe_and_clear_stale_artifacts():
    page = (
        Path(__file__).resolve().parents[2] / "pages" / "18_NEMA_AGORA.py"
    ).read_text(encoding="utf-8")
    reload = page.index('"Prepare / reload evidence case"')
    load_handler = page.index("except Exception as exc:", reload)
    clear_bundle = page.index('st.session_state.pop(f"evidence_bundle_{selected_id}", None)', load_handler)
    clear_export = page.index('st.session_state.pop(f"evidence_export_{selected_id}", None)', clear_bundle)
    safe_message = page.index(
        "The evidence case could not be loaded. Check access and storage health, then retry.",
        load_handler,
    )
    assert reload < load_handler < clear_bundle < clear_export < safe_message


def test_review_export_and_intelligence_failures_have_safe_messages():
    page = (
        Path(__file__).resolve().parents[2] / "pages" / "18_NEMA_AGORA.py"
    ).read_text(encoding="utf-8")
    for message in (
        "The review could not be confirmed as saved. Reload the case before retrying.",
        "The export could not be confirmed. Reload the case before attempting another export.",
        "The reviewer brief could not be prepared. Check access and service health, then retry.",
        "Shadow analysis could not be completed. Check access and service health, then retry.",
    ):
        assert message in page


def test_release_readiness_failures_do_not_leak_exception_details_or_claim_approval():
    page = (
        Path(__file__).resolve().parents[2] / "pages" / "18_NEMA_AGORA.py"
    ).read_text(encoding="utf-8")
    action = page.index('st.button("Evaluate release readiness"')
    handler = page.index("except Exception as exc:", action)
    safe_message_start = page.index(
        "Readiness could not be evaluated. Check the candidate SHA and evidence JSON,",
        handler,
    )
    safe_message_end = page.index(
        "then retry. No release approval was granted.",
        safe_message_start,
    )
    assert action < handler < safe_message_start < safe_message_end
    assert "st.caption(f\"Failure type: {type(exc).__name__}\")" in page[safe_message_end:]

def test_operational_backup_controls_are_admin_gated_and_fail_closed():
    page = (
        Path(__file__).resolve().parents[2] / "pages" / "18_NEMA_AGORA.py"
    ).read_text(encoding="utf-8")
    section = page.index('governance_tool == "Operations & backups"')
    gate = page.index('principal.role != "admin"', section)
    backup_config = page.index("backup_dir_from_secrets(st.secrets)", gate)
    integrity_gate = page.index("elif not db_healthy:", backup_config)
    backup_action = page.index('st.button("Create verified backup"', integrity_gate)
    retention_action = page.index('st.button("Apply backup retention"', backup_action)
    assert section < gate < backup_config < integrity_gate < backup_action < retention_action
    assert "Backups may contain environmental case records" in page[section:]
    assert "does not prove off-site recovery" in page[section:]

def test_restore_is_admin_gated_and_requires_two_explicit_confirmations():
    page = (
        Path(__file__).resolve().parents[2] / "pages" / "18_NEMA_AGORA.py"
    ).read_text(encoding="utf-8")
    section = page.index('governance_tool == "Operations & backups"')
    admin_gate = page.index('principal.role != "admin"', section)
    restore_section = page.index('st.markdown("**Restore from a verified backup**")', admin_gate)
    checkbox = page.index("I understand this replaces current database contents.", restore_section)
    typed_phrase = page.index("Type RESTORE DATABASE to enable restore", checkbox)
    disabled_guard = page.index("disabled=not (confirm_restore and typed_confirmation == \"RESTORE DATABASE\")", typed_phrase)
    pre_backup = page.index("pre_restore_backup = backup_database(database_path, backup_dir)", disabled_guard)
    destructive_restore = page.index("confirm_destructive=True", pre_backup)
    assert section < admin_gate < restore_section < checkbox < typed_phrase < disabled_guard < pre_backup < destructive_restore
    assert "Coordinate a maintenance window" in page[restore_section:]



def test_workspace_overview_has_task_shortcuts_and_safe_record_scope():
    page = (
        Path(__file__).resolve().parents[2] / "pages" / "18_NEMA_AGORA.py"
    ).read_text(encoding="utf-8")
    assert '"Workspace overview"' in page
    assert 'st.button("Open observation form"' in page
    assert 'st.button("Open case management"' in page
    assert 'st.button("Open intelligence"' in page
    assert "records_for_current_user()" in page
    assert "not verified environmental outcomes" in page
    assert "Governance & operations" in page


def test_navigation_uses_one_curated_page_with_grouped_work_areas():
    app = (Path(__file__).resolve().parents[2] / "app.py").read_text(encoding="utf-8")
    page = (
        Path(__file__).resolve().parents[2] / "pages" / "18_NEMA_AGORA.py"
    ).read_text(encoding="utf-8")
    assert 'st.Page("pages/18_NEMA_AGORA.py", title="NEMA-AGORA")' in app
    assert '"Intelligence workspace": "🧠  Intelligence & AI"' in page
    assert '"Maps & metrics": "🗺️  Maps & monitoring"' in page
    assert '"Governance & help": "🛡️  Governance & operations"' in page
