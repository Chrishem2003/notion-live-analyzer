"""Navigation contract tests: one visible NEMA-AGORA destination only."""
from pathlib import Path


def test_single_nema_agora_workspace_is_the_only_nema_page_in_current_app():
    root = Path(__file__).resolve().parents[2]
    pages = root / "pages"
    visible_nema_pages = sorted(path.name for path in pages.glob("*NEMA_AGORA*.py"))
    assert visible_nema_pages == ["18_NEMA_AGORA.py"]


def test_current_main_application_shell_is_preserved():
    root = Path(__file__).resolve().parents[2]
    app = root / "app.py"
    source = app.read_text(encoding="utf-8")
    assert "Chrishem Science Hub" in source
    assert "ensure_bootstrap_admin_record" in source


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

def test_spatial_evidence_requires_explicit_alignment_attestation():
    page = (
        Path(__file__).resolve().parents[2] / "pages" / "18_NEMA_AGORA.py"
    ).read_text(encoding="utf-8")

    checkbox = page.index('alignment_confirmed = st.checkbox(')
    default_unchecked = page.index('value=False,', checkbox)
    attestation_warning = page.index(
        "This is an operator attestation, not independent geospatial verification.",
        checkbox,
    )
    quality_call = page.index("quality_evidence = spatial_temporal_quality_evidence(", checkbox)
    conditional_alignment = page.index(
        'spatial_alignment="ALIGNED" if alignment_confirmed else "UNVERIFIED"',
        quality_call,
    )
    baseline_aoi = page.index('baseline_aoi_id = st.text_input("Baseline AOI ID"', checkbox)
    comparison_aoi = page.index('comparison_aoi_id = st.text_input("Comparison AOI ID"', baseline_aoi)
    baseline_grid = page.index('baseline_grid_id = st.text_input("Baseline aligned grid ID"', comparison_aoi)
    comparison_grid = page.index('comparison_grid_id = st.text_input("Comparison aligned grid ID"', baseline_grid)
    assert checkbox < default_unchecked < attestation_warning < baseline_aoi < comparison_aoi < baseline_grid < comparison_grid < quality_call < conditional_alignment
    assert "baseline_aoi_id=baseline_aoi_id.strip()" in page
    assert "comparison_aoi_id=comparison_aoi_id.strip()" in page
    assert "baseline_grid_id=baseline_grid_id.strip()" in page
    assert "comparison_grid_id=comparison_grid_id.strip()" in page
