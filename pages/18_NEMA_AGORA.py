"""NEMA-AGORA: authenticated pilot workspace.

Demo mode is session-only and safe for synthetic testing. Persistent mode is
explicitly opt-in and requires Streamlit OIDC plus a server-side role binding.
This remains an independent student-led prototype, not an official NEMA service.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import pandas as pd
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import resolve_principal
from nema_agora.config import (
    backup_dir_from_secrets,
    backup_retention_from_secrets,
    database_path_from_secrets,
    mode_from_secrets,
)
from nema_agora.backup import backup_database, integrity_check, list_backups, prune_backups, restore_database
from nema_agora.core import CATEGORIES, SEVERITIES, STATUSES, make_observation, validate_observation
from nema_agora.governance import policy_from_secrets, validate_governance
from nema_agora.quality import assess_observation
from nema_agora.evidence_case import validate_evidence_case
from nema_agora.service import NemaAgoraService
from nema_agora.runtime import initialize_persistent_service
from nema_agora.workflow import ALLOWED_TRANSITIONS, apply_status_update
from nema_agora.release_readiness import evaluate_release_readiness, validate_release_readiness_report
from nema_agora.spatial_temporal_change import spatial_temporal_change_evidence
from nema_agora.spatial_temporal_quality import spatial_temporal_quality_evidence
from nema_agora.spatial_change_detection import detect_candidate
from nema_agora.spatial_workspace_bundle import build_spatial_evidence_bundle, validate_spatial_evidence_bundle
from nema_agora.source_registry import list_sources
from nema_agora.asset_receipt import build_manual_asset_receipt, validate_asset_receipt
from nema_agora.geojson_aoi import validate_geojson_aoi
from nema_agora.paired_study_manifest import build_paired_study_manifest, validate_paired_study_manifest
from nema_agora.paired_raster_array_analysis import analyze_paired_raster_arrays, validate_paired_array_analysis
from nema_agora.geotiff_ingestion import read_geotiff_scene

st.set_page_config(page_title="NEMA-AGORA | Environmental Workspace", page_icon="🌿", layout="wide")

# Lightweight visual system: clear hierarchy, consistent spacing and readable
# navigation without relying on custom frontend packages.
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-top: 1.6rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        line-height: 1.45;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        padding-top: .28rem;
        padding-bottom: .28rem;
    }
    [data-testid="stMetric"] {
        border: 1px solid rgba(128, 128, 128, .22);
        padding: .8rem 1rem;
        border-radius: .8rem;
    }
    div[data-testid="stForm"] {
        border: 1px solid rgba(128, 128, 128, .20);
        border-radius: .8rem;
        padding: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _demo_init() -> None:
    st.session_state.setdefault("nema_agora_reports", [])
    st.session_state.setdefault("nema_agora_audit_events", [])


def _persistent_context() -> tuple[NemaAgoraService | None, object | None, str]:
    mode = mode_from_secrets(st.secrets)
    if mode != "persistent":
        return None, None, mode
    principal = resolve_principal(st)
    if principal is None or not principal.is_authorised:
        return None, principal, mode
    database_path = database_path_from_secrets(st.secrets)
    if database_path is None:
        st.error("Persistent mode is enabled but nema_agora.database_path is not configured.")
        return None, principal, mode
    try:
        service = initialize_persistent_service(database_path)
    except Exception as exc:
        # Avoid leaking filesystem paths, SQL details, or secrets in the UI.
        st.error(
            "Persistent storage is temporarily unavailable. No demo fallback was started. "
            "Check the deployment storage configuration and application logs, then retry."
        )
        st.caption(f"Failure type: {type(exc).__name__}")
        return None, principal, mode
    return service, principal, mode


_demo_init()
service, principal, mode = _persistent_context()
if mode == "invalid":
    st.error("NEMA-AGORA mode configuration is invalid. Set nema_agora.mode explicitly to \"demo\" or \"persistent\"; no workspace mode was started.")
    st.stop()

# Persistent mode must never fall through to session-only demo records. Require
# an authenticated, provisioned principal and a working persistent service
# before rendering any workspace workflows or data.
if mode == "persistent":
    if principal is None:
        st.warning("Sign in is required before the persistent NEMA-AGORA workspace can be opened.")
        if hasattr(st, "login") and st.button("Sign in", type="primary", use_container_width=True):
            st.login()
        st.stop()
    if not principal.is_authorised:
        st.error("This account is authenticated but is not provisioned for the NEMA-AGORA pilot.")
        if hasattr(st, "logout") and st.button("Sign out", use_container_width=True):
            st.logout()
        st.stop()
    if service is None:
        st.stop()

governance_policy = policy_from_secrets(st.secrets)
governance_errors = validate_governance(governance_policy)
if governance_errors:
    st.error("NEMA-AGORA governance configuration is invalid; data intake is disabled.")
    for error in governance_errors:
        st.error(error)
    st.stop()

st.title("🌿 NEMA-AGORA")
st.caption("Environmental Governance, Monitoring & Response")
st.markdown(
    "A single workspace for **observation intake, case review, environmental evidence, "
    "monitoring metrics, and operational governance**. Choose a work area from the sidebar."
)
st.info(
    "Pilot prototype — not an official NEMA service. It does not submit reports to NEMA "
    "or connect to ELMIS/SWIMS. Use synthetic or appropriately consented test records; "
    "do not enter personal, confidential, or urgent incident information."
)

with st.sidebar:
    st.header("Security & data mode")
    if mode == "persistent":
        st.success("Persistent mode")
        if principal is None:
            st.warning("Authentication required before persistent data is available.")
            if hasattr(st, "login") and st.button("Sign in", type="primary", use_container_width=True):
                st.login()
        elif not principal.is_authorised:
            st.error("Authenticated, but not provisioned for this pilot.")
            st.write(f"Account: {principal.display_name or principal.subject}")
            if hasattr(st, "logout") and st.button("Sign out", use_container_width=True):
                st.logout()
        else:
            st.success(f"Signed in as {principal.display_name or principal.subject}")
            st.caption(f"Role: {principal.role}")
            if hasattr(st, "logout") and st.button("Sign out", use_container_width=True):
                st.logout()
    else:
        st.warning("Demo mode — session-only")
        st.caption("Persistent storage is disabled until explicitly configured.")
    st.divider()
    st.write("**Workflow:** report → validate → quality → review → controlled export.")
    st.write("**Intelligence:** advisory analysis → human verification → decision.")
    st.write("**Safety:** synthetic/consented test records only.")
    st.markdown("[Project source on GitHub](https://github.com/Chrishem2003/notion-live-analyzer)")
    st.divider()
    st.subheader("Workspace")
    st.caption("Choose one work area. Related tools are grouped inside each section.")
    active_section = st.radio(
        "Choose a work area",
        [
            "Workspace overview",
            "Submit observation",
            "Case management",
            "Intelligence workspace",
            "Maps & metrics",
            "Governance & help",
        ],
        index=0,
        key="nema_agora_navigation",
        label_visibility="collapsed",
        format_func=lambda value: {
            "Workspace overview": "🏠  Overview",
            "Submit observation": "📝  Capture observation",
            "Case management": "📂  Case management",
            "Intelligence workspace": "🧠  Intelligence & AI",
            "Maps & metrics": "🗺️  Maps & monitoring",
            "Governance & help": "🛡️  Governance & operations",
        }.get(value, value),
        help="Overview gives you a summary and shortcuts. Each work area contains its own related tools.",
    )

if mode == "persistent" and (principal is None or not principal.is_authorised):
    st.stop()

persistent = service is not None and principal is not None and principal.is_authorised


def records_for_current_user() -> list[dict]:
    if persistent:
        return service.list_observations(principal)
    return list(st.session_state.nema_agora_reports)


def save_record(record: dict) -> None:
    quality = assess_observation(record, peer_records=records_for_current_user())
    record["quality_status"] = quality["quality_status"]
    record["quality_flags"] = quality["flags"]
    if persistent:
        service.create_observation(record, principal)
    else:
        st.session_state.nema_agora_reports.append(record)


def visible_audit(case_id: str) -> list[dict]:
    if persistent:
        return service.list_audit_events(case_id, principal)
    return [e for e in st.session_state.nema_agora_audit_events if e["case_id"] == case_id]


can_review = persistent and has_permission(principal.role, "observation:review")
can_export = persistent and has_permission(principal.role, "case:export")
can_metrics = persistent and has_permission(principal.role, "metrics:read")
can_audit = persistent and has_permission(principal.role, "audit:read")
can_intelligence = persistent and has_permission(principal.role, "intelligence:use")
can_shadow = persistent and has_permission(principal.role, "intelligence:shadow")


def _go_to_section(section: str) -> None:
    """Switch the sidebar radio before the next Streamlit rerun."""
    st.session_state["nema_agora_navigation"] = section


if active_section == "Workspace overview":
    st.subheader("Workspace overview")
    st.caption("Start here to see the current pilot state and move directly to a task.")

    if persistent and not can_metrics:
        visible_records = records_for_current_user()
        st.caption("Record totals reflect only records visible to your account.")
    else:
        visible_records = records_for_current_user()

    total_records = len(visible_records)
    needs_review = sum(1 for item in visible_records if item.get("status") in ("Received", "Under review"))
    progressed = sum(1 for item in visible_records if item.get("status") not in ("Received",))
    closed_records = sum(1 for item in visible_records if item.get("status") == "Closed")

    metric_cols = st.columns(4)
    metric_cols[0].metric("Visible records", total_records)
    metric_cols[1].metric("Awaiting / in review", needs_review)
    metric_cols[2].metric("Progressed", progressed)
    metric_cols[3].metric("Closed", closed_records)

    if mode == "demo":
        st.warning("Demo mode: records are session-only and may disappear when the session ends.")
    elif persistent:
        st.success(f"Persistent workspace · signed in as {principal.display_name or principal.subject} · role: {principal.role}")
    else:
        st.info("Persistent data is not available until authentication and server-side role provisioning succeed.")

    st.markdown("### Quick actions")
    action_cols = st.columns(3)
    with action_cols[0]:
        st.markdown("**📝 Capture**")
        st.caption("Record an observation and run initial quality checks.")
        st.button("Open observation form", key="overview_capture", type="primary", use_container_width=True,
                  on_click=_go_to_section, args=("Submit observation",))
    with action_cols[1]:
        st.markdown("**📂 Review cases**")
        st.caption("Inspect case status, human review and authorised audit history.")
        st.button("Open case management", key="overview_cases", use_container_width=True,
                  on_click=_go_to_section, args=("Case management",))
    with action_cols[2]:
        st.markdown("**🧠 Explore evidence**")
        st.caption("Use advisory intelligence and spatial evidence tools.")
        st.button("Open intelligence", key="overview_intelligence", use_container_width=True,
                  on_click=_go_to_section, args=("Intelligence workspace",))

    st.markdown("### Work areas")
    overview_rows = [
        ("📝 Capture observation", "Structured intake, consent confirmation and data-quality feedback."),
        ("📂 Case management", "Valid workflow transitions, reviewer notes, provenance and controlled exports."),
        ("🧠 Intelligence & AI", "Evidence analysis, reviewer copilot, shadow evaluation and observatory."),
        ("🗺️ Maps & monitoring", "Map views, pilot metrics and spatial change evidence."),
        ("🛡️ Governance & operations", "Release evidence, admin-only backup controls and pilot guidance."),
    ]
    for label, description in overview_rows:
        with st.container(border=True):
            st.markdown(f"**{label}**")
            st.caption(description)

    st.caption("Prototype metrics describe records in this workspace; they are not verified environmental outcomes or official response statistics.")


# Keep secondary navigation local to the chosen work area so users see only
# one task surface at a time instead of a long, vertically stacked dashboard.
intelligence_tool = None
map_tool = None
governance_tool = None
if active_section == "Intelligence workspace":
    intelligence_tool = st.radio(
        "Intelligence tools",
        ["Evidence intelligence", "Reviewer copilot", "AI shadow mode", "Evaluation observatory"],
        horizontal=True,
        key="nema_agora_intelligence_tool",
    )
elif active_section == "Maps & metrics":
    map_tool = st.radio(
        "View",
        ["Map", "Pilot metrics", "Spatial evidence", "Data sources & asset receipts"],
        horizontal=True,
        key="nema_agora_map_tool",
    )
elif active_section == "Governance & help":
    governance_tool = st.radio(
        "Governance tools",
        ["Release readiness", "Operations & backups", "About the pilot"],
        horizontal=True,
        key="nema_agora_governance_tool",
    )

# One Streamlit page with short, task-oriented navigation.

if active_section == "Submit observation":
    st.subheader("Record an environmental observation")
    st.caption("Use only synthetic or consented test information during development.")
    if not persistent and mode == "demo":
        st.caption("Demo records disappear when the Streamlit session ends.")
    with st.form("nema_agora_report_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            category = st.selectbox("Observation category", CATEGORIES)
            observation_date = st.date_input("Date observed", value=date.today())
            site = st.text_input("District / site label", placeholder="e.g. Pilot site A", max_chars=120)
            allowed_severities = tuple(s for s in SEVERITIES if governance_policy["allow_urgent_incidents"] or s != "Urgent")
            severity = st.selectbox("Initial priority (unverified)", allowed_severities, index=min(1, len(allowed_severities) - 1))
        with c2:
            latitude = st.number_input("Latitude (optional)", min_value=-90.0, max_value=90.0, value=0.0, step=0.0001, format="%.5f")
            longitude = st.number_input("Longitude (optional)", min_value=-180.0, max_value=180.0, value=0.0, step=0.0001, format="%.5f")
            evidence_reference = st.text_input("Evidence reference (optional; unverified pointer)", placeholder="Non-sensitive file name or URL", max_chars=300)
        description = st.text_area("Observation description", placeholder="Describe what was observed, when, and from what safe/public vantage point.", max_chars=1500)
        consent_confirmed = st.checkbox("I have permission to submit this test record and have removed unnecessary personal details.")
        submitted = st.form_submit_button("Save pilot record", type="primary", use_container_width=True)
    if submitted:
        errors = validate_observation(site=site, description=description, consent_confirmed=consent_confirmed)
        if errors:
            for error in errors:
                st.error(error)
        else:
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            try:
                record = make_observation(
                    observation_date=observation_date, category=category, severity=severity,
                    site=site, description=description, latitude=latitude, longitude=longitude,
                    consent_confirmed=consent_confirmed, created_at=now,
                    evidence_reference=evidence_reference,
                )
                save_record(record)
            except (ValueError, PermissionError) as exc:
                st.error(str(exc))
            else:
                quality = assess_observation(record, peer_records=records_for_current_user())
                if quality["quality_status"] == "PASS":
                    st.success(f"Pilot record saved: {record['case_id']} — quality check passed")
                else:
                    st.warning(f"Pilot record saved: {record['case_id']} — review required: {', '.join(quality['flags'])}")

if active_section == "Case management":
    st.subheader("Review queue and case status")
    if not persistent:
        st.info("Review controls are disabled in demo mode. Persistent review requires an authenticated reviewer or coordinator.")
    elif not can_review:
        st.info("Your account is not assigned review permission.")
    else:
        records = records_for_current_user()
        if not records:
            st.info("No records available. Submit a pilot observation first, or switch to an account with authorised case access.")
        else:
            status_counts = {status: sum(1 for item in records if item.get("status") == status) for status in STATUSES}
            queue_cols = st.columns(len(STATUSES))
            for idx, status in enumerate(STATUSES):
                queue_cols[idx].metric(status, status_counts.get(status, 0))

            st.markdown("### Find a case")
            filter_cols = st.columns([2, 1, 1, 1])
            with filter_cols[0]:
                case_query = st.text_input(
                    "Search cases",
                    placeholder="Case ID, site, category, or description",
                    key="nema_case_search",
                ).strip().casefold()
            with filter_cols[1]:
                status_filter = st.selectbox(
                    "Status filter", ["All statuses", *STATUSES], key="nema_case_status_filter"
                )
            with filter_cols[2]:
                category_filter = st.selectbox(
                    "Category filter", ["All categories", *CATEGORIES], key="nema_case_category_filter"
                )
            with filter_cols[3]:
                severity_filter = st.selectbox(
                    "Priority filter", ["All priorities", *SEVERITIES], key="nema_case_severity_filter"
                )

            filtered_records = [
                item for item in records
                if (status_filter == "All statuses" or item.get("status") == status_filter)
                and (category_filter == "All categories" or item.get("category") == category_filter)
                and (severity_filter == "All priorities" or item.get("severity") == severity_filter)
                and (
                    not case_query
                    or case_query in " ".join(
                        str(item.get(field, "")) for field in
                        ("case_id", "district_or_site", "category", "description", "severity")
                    ).casefold()
                )
            ]
            st.caption(f"Showing {len(filtered_records)} of {len(records)} records in the queue below. The case selector includes all records visible to your account.")
            selected_id = st.selectbox("Select record to review (all visible cases)", options=[r["case_id"] for r in reversed(records)])
            selected = next(r for r in records if r["case_id"] == selected_id)
            st.markdown(f"**{selected['category']}** · {selected['severity']} · {selected['district_or_site']}")
            st.write(selected["description"])
            st.caption(f"Observed: {selected['observation_date']} · Created: {selected['created_at']}")
            provenance = selected.get("evidence_provenance", "legacy_or_unknown")
            verification = selected.get("evidence_verification_status", "unverified")
            st.caption(
                f"Evidence provenance: {provenance.replace('_', ' ')} · "
                f"Verification: {verification.replace('_', ' ')}"
            )
            if selected.get("evidence_reference"):
                st.info(
                    "Evidence reference is a user-supplied pointer only. The referenced file or URL "
                    "has not been independently verified by this pilot."
                )
            quality = assess_observation(selected, peer_records=records)
            st.markdown(f"**Data quality:** {quality['quality_status']} · {', '.join(quality['flags'])}")
            st.caption(
                "Workflow run: choose the next case status, add a concise review note, then submit the transition. "
                "Only authorised reviewers can run this step; the transition is validated and audit-recorded by the service."
            )
            with st.form(f"review_{selected_id}"):
                permitted_statuses = [
                    status for status in STATUSES
                    if status == selected["status"] or status in ALLOWED_TRANSITIONS[selected["status"]]
                ]
                new_status = st.selectbox(
                    "Next workflow status",
                    permitted_statuses,
                    index=permitted_statuses.index(selected["status"]),
                    help="Only valid next steps for the current status are shown.",
                )
                review_notes = st.text_area("Reviewer notes (avoid personal/sensitive data)", value=selected.get("review_notes", ""), max_chars=1000)
                reviewed = st.form_submit_button("Run workflow transition", type="primary")
            if reviewed:
                changed_at = datetime.now().astimezone().isoformat(timespec="seconds")
                try:
                    service.update_review(selected_id, principal, new_status=new_status, review_notes=review_notes, changed_at=changed_at)
                except (ValueError, PermissionError, KeyError) as exc:
                    st.error("The review could not be confirmed as saved. Reload the case and verify its current status before retrying.")
                    st.caption(f"Failure type: {type(exc).__name__}")
                except Exception as exc:
                    # Keep storage/driver details out of the user-facing page.
                    st.error("The review could not be confirmed as saved because the workflow service encountered an unexpected error. Reload the case before retrying.")
                    st.caption(f"Failure type: {type(exc).__name__}")
                else:
                    st.success("Record updated and workflow transition confirmed.")
                    st.rerun()
            if can_audit:
                events = visible_audit(selected_id)
                if events:
                    st.markdown("**Audit history**")
                    st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
            st.divider()
            if filtered_records:
                queue_frame = pd.DataFrame(filtered_records)[
                    ["case_id", "observation_date", "category", "severity", "district_or_site", "status"]
                ].rename(columns={
                    "case_id": "Case ID",
                    "observation_date": "Observed",
                    "category": "Category",
                    "severity": "Priority (unverified)",
                    "district_or_site": "Site",
                    "status": "Workflow status",
                })
                st.dataframe(queue_frame, use_container_width=True, hide_index=True)
            else:
                st.info("No cases match these filters. Clear the search or reset the status, category, and priority filters.")
            if can_export:
                st.download_button(
                    "Download authorised records as CSV",
                    data=service.export_csv(principal, records_for_current_user()),
                    file_name="nema_agora_records.csv", mime="text/csv", use_container_width=True,
                )
            elif persistent:
                st.caption("CSV export is restricted to coordinator/admin roles.")

            st.divider()
            st.subheader("Evidence provenance & governed export")
            st.caption(
                "Persists a provenance-bound evidence bundle and records each human review/export transition. "
                "External references are pointers only; they are not proof that file contents were verified."
            )
            if st.button(
                "Prepare / reload evidence case",
                key=f"prepare_evidence_{selected_id}",
                use_container_width=True,
            ):
                # Invalidate prior derived UI state before attempting a fresh load.
                # If the store call fails, old bundle/export data must not look current.
                st.session_state.pop(f"evidence_bundle_{selected_id}", None)
                st.session_state.pop(f"evidence_export_{selected_id}", None)
                try:
                    prepared_bundle = service.build_governed_evidence_case(selected_id, principal)
                    st.session_state[f"evidence_bundle_{selected_id}"] = prepared_bundle["evidence_case"]
                    st.success("Evidence bundle loaded from the governed workflow store.")
                except Exception as exc:
                    st.session_state.pop(f"evidence_bundle_{selected_id}", None)
                    st.session_state.pop(f"evidence_export_{selected_id}", None)
                    st.error("The evidence case could not be loaded. Check access and storage health, then retry.")
                    st.caption(f"Failure type: {type(exc).__name__}")

            governed_bundle = st.session_state.get(f"evidence_bundle_{selected_id}")
            if governed_bundle is not None:
                integrity = validate_evidence_case(governed_bundle)
                st.write(f"**Evidence-case state:** {governed_bundle.state}")
                st.write(f"**Integrity:** {'VALID' if integrity['valid'] else 'INVALID'}")
                if not integrity["valid"]:
                    st.error(", ".join(integrity["issues"]))
                st.caption(f"Provenance fingerprint: {governed_bundle.provenance_fingerprint}")
                if governed_bundle.state == "READY_FOR_REVIEW" and integrity["valid"]:
                    with st.form(f"governed_review_{selected_id}"):
                        governed_decision = st.selectbox(
                            "Human evidence decision",
                            ["ACKNOWLEDGED", "REQUIRES_FOLLOW_UP", "ESCALATED"],
                            key=f"governed_decision_{selected_id}",
                        )
                        governed_notes = st.text_area(
                            "Evidence review notes (no personal or confidential details)",
                            max_chars=1000,
                            key=f"governed_notes_{selected_id}",
                        )
                        save_governed_review = st.form_submit_button(
                            "Save signed-in reviewer decision", type="primary"
                        )
                    if save_governed_review:
                        try:
                            reviewed_bundle = service.review_governed_evidence_case(
                                governed_bundle, principal,
                                decision=governed_decision, notes=governed_notes,
                                reviewed_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                            )
                            st.session_state[f"evidence_bundle_{selected_id}"] = reviewed_bundle
                            st.session_state.pop(f"evidence_export_{selected_id}", None)
                        except Exception as exc:
                            st.session_state.pop(f"evidence_bundle_{selected_id}", None)
                            st.session_state.pop(f"evidence_export_{selected_id}", None)
                            st.error("The review could not be confirmed as saved. Reload the case before retrying.")
                            st.caption(f"Failure type: {type(exc).__name__}")
                        else:
                            st.success("Human review persisted with actor-bound audit history.")
                            st.rerun()
                elif governed_bundle.state == "REVIEWED" and can_export and integrity["valid"]:
                    if st.button(
                        "Generate governed JSON export",
                        key=f"governed_export_{selected_id}",
                        type="primary",
                    ):
                        try:
                            export_bytes = service.export_governed_evidence_case(governed_bundle, principal)
                            st.session_state[f"evidence_export_{selected_id}"] = export_bytes
                            st.session_state.pop(f"evidence_bundle_{selected_id}", None)
                        except Exception as exc:
                            st.session_state.pop(f"evidence_bundle_{selected_id}", None)
                            st.session_state.pop(f"evidence_export_{selected_id}", None)
                            st.error("The export could not be confirmed. Reload the case before attempting another export.")
                            st.caption(f"Failure type: {type(exc).__name__}")
                        else:
                            st.success("Integrity-checked export recorded. Refresh the evidence case to inspect its final state.")
                            st.rerun()
                elif governed_bundle.state == "REVIEWED" and not can_export:
                    st.info("Human review is recorded. JSON export is restricted to coordinator/admin roles.")
                elif governed_bundle.state == "EXPORTED":
                    st.success("This evidence case is already marked exported; it cannot be exported again through this transition.")
            export_bytes = st.session_state.get(f"evidence_export_{selected_id}")
            if export_bytes:
                st.download_button(
                    "Download governed evidence JSON",
                    data=export_bytes,
                    file_name=f"{selected_id}_evidence.json",
                    mime="application/json",
                    key=f"download_evidence_{selected_id}",
                    use_container_width=True,
                )
            if can_audit and st.checkbox(
                "Show evidence-case transition audit",
                key=f"show_evidence_audit_{selected_id}",
            ):
                try:
                    evidence_events = service.list_evidence_case_events(selected_id, principal)
                except Exception as exc:
                    st.error("The evidence audit trail could not be loaded. Check access and storage health.")
                    st.caption(f"Failure type: {type(exc).__name__}")
                else:
                    if evidence_events:
                        st.dataframe(pd.DataFrame(evidence_events), use_container_width=True, hide_index=True)
                    else:
                        st.info("No governed evidence transitions recorded yet.")

if active_section == "Intelligence workspace" and intelligence_tool == "Evidence intelligence":
    st.subheader("🧠 Evidence intelligence — human-in-the-loop")
    st.caption("Phase 8–10 foundation: deterministic, explainable, evaluated and advisory. No autonomous regulatory or enforcement decisions are made.")
    if not persistent:
        st.info("Intelligence controls are available after authenticated persistent deployment. Demo mode remains session-only.")
    elif not can_intelligence:
        st.info("Your account is not assigned evidence-intelligence permission.")
    else:
        records = records_for_current_user()
        if not records:
            st.info("No records available for analysis.")
        else:
            selected_ai_id = st.selectbox("Observation to analyse", options=[r["case_id"] for r in reversed(records)], key="intelligence_case")
            selected_ai = next(r for r in records if r["case_id"] == selected_ai_id)
            if st.button("Run advisory analysis", type="primary", use_container_width=True):
                try:
                    analysis = service.analyze_observation(selected_ai, principal, peer_records=records)
                except Exception as exc:
                    st.error("Advisory analysis could not be completed. No case status or observation data was changed.")
                    st.caption(f"Failure type: {type(exc).__name__}")
                else:
                    st.markdown("### Neutral summary")
                    st.write(analysis["summary"])
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Quality", analysis["quality_status"])
                    c2.metric("Review", "Required" if analysis["human_review_required"] else "Not required")
                    c3.metric("Advisory", analysis["priority_advisory"]["level"])
                    st.markdown("### Quality signals")
                    st.write(", ".join(analysis["quality_flags"]))
                    st.markdown("### Category suggestions")
                    if analysis["category_suggestions"]:
                        st.dataframe(pd.DataFrame(analysis["category_suggestions"]), use_container_width=True, hide_index=True)
                    else:
                        st.info("No keyword-supported alternative category was generated.")
                    st.markdown("### Duplicate candidates")
                    if analysis["duplicate_candidates"]:
                        st.write(", ".join(analysis["duplicate_candidates"]))
                        st.warning("Possible duplicates must be reviewed by a person; no record is deleted or automatically merged.")
                    else:
                        st.info("No deterministic duplicate candidate found.")
                    st.markdown("### Review-priority rationale")
                    st.write(analysis["priority_advisory"]["reason"])
                    st.warning(analysis["decision_notice"])

if active_section == "Intelligence workspace" and intelligence_tool == "Reviewer copilot":
    st.subheader("🤝 Reviewer copilot")
    st.caption("Phase 10: structured reviewer assistance built from supplied evidence. Recommendations never change case status.")
    if not persistent:
        st.info("Reviewer copilot is available only in authenticated persistent mode.")
    elif not can_intelligence:
        st.info("Your account is not assigned evidence-intelligence permission.")
    else:
        records = records_for_current_user()
        if not records:
            st.info("No records available for copilot review.")
        else:
            selected_copilot_id = st.selectbox(
                "Observation for reviewer assistance",
                options=[r["case_id"] for r in reversed(records)],
                key="copilot_case",
            )
            selected_copilot = next(r for r in records if r["case_id"] == selected_copilot_id)
            if st.button("Prepare reviewer brief", type="primary", use_container_width=True):
                # A failed rerun must not leave a prior brief looking freshly prepared.
                st.session_state.pop("nema_agora_copilot_brief", None)
                st.session_state.pop("nema_agora_copilot_case", None)
                try:
                    brief = service.build_reviewer_copilot(
                        selected_copilot, principal, peer_records=records
                    )
                    st.session_state["nema_agora_copilot_brief"] = brief
                    st.session_state["nema_agora_copilot_case"] = selected_copilot_id
                except Exception as exc:
                    st.session_state.pop("nema_agora_copilot_brief", None)
                    st.session_state.pop("nema_agora_copilot_case", None)
                    st.error("The reviewer brief could not be prepared. Check access and service health, then retry.")
                    st.caption(f"Failure type: {type(exc).__name__}")

            brief = st.session_state.get("nema_agora_copilot_brief")
            if brief and st.session_state.get("nema_agora_copilot_case") == selected_copilot_id:
                st.success("Reviewer brief prepared. Human judgement remains authoritative.")
                st.markdown("### Evidence actually supplied")
                facts = brief["evidence_facts"]
                if facts:
                    st.dataframe(pd.DataFrame(facts), use_container_width=True, hide_index=True)
                else:
                    st.info("No evidence fields were available.")
                st.markdown("### Quality gate")
                st.write(f"**{brief['quality']['status']}**")
                if brief["quality"]["flags"]:
                    st.warning(", ".join(brief["quality"]["flags"]))
                st.markdown("### Category review")
                st.write(f"Supplied category: **{brief['category_review']['supplied_category']}**")
                if brief["category_review"]["suggestions"]:
                    st.dataframe(pd.DataFrame(brief["category_review"]["suggestions"]), use_container_width=True, hide_index=True)
                else:
                    st.info("No alternative category suggestion was generated.")
                st.markdown("### Duplicate review")
                candidates = brief["duplicate_review"]["candidate_case_ids"]
                st.write(", ".join(candidates) if candidates else "No candidate found.")
                if candidates:
                    st.warning("Candidate matches require human comparison; no automatic merge or deletion occurs.")
                st.markdown("### Questions for the reviewer")
                for question in brief["uncertainty_questions"]:
                    st.write(f"• {question}")
                st.markdown("### Reviewer checklist")
                for item in brief["review_checklist"]:
                    st.checkbox(item, key=f"copilot_check_{selected_copilot_id}_{item[:20]}")
                st.warning(brief["decision_notice"])

                st.markdown("### Capture reviewer feedback")
                st.caption("Feedback improves evaluation evidence; it does not alter the observation or its workflow state.")
                with st.form(f"copilot_feedback_{selected_copilot_id}"):
                    feedback_type = st.radio(
                        "How was the copilot category guidance?",
                        ["accepted", "rejected", "corrected"],
                        horizontal=True,
                    )
                    corrected_category = ""
                    if feedback_type == "corrected":
                        corrected_category = st.selectbox(
                            "Correct category",
                            CATEGORIES,
                            key=f"corrected_category_{selected_copilot_id}",
                        )
                    feedback_notes = st.text_area(
                        "Reviewer note (no personal/confidential information)",
                        max_chars=1000,
                        key=f"feedback_notes_{selected_copilot_id}",
                    )
                    feedback_saved = st.form_submit_button("Save evaluation feedback", type="primary")
                if feedback_saved:
                    try:
                        service.record_intelligence_feedback(
                            selected_copilot_id,
                            principal,
                            feedback={
                                "feedback_type": feedback_type,
                                "corrected_category": corrected_category,
                                "notes": feedback_notes,
                                "copilot_version": brief["copilot_version"],
                            },
                            occurred_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                        )
                    except (ValueError, PermissionError, KeyError) as exc:
                        st.error(str(exc))
                    else:
                        st.success("Feedback recorded in the pilot evaluation trail.")

                if can_audit:
                    try:
                        events = service.list_intelligence_events(selected_copilot_id, principal)
                    except (PermissionError, KeyError):
                        events = []
                    if events:
                        st.markdown("### Intelligence audit trail")
                        st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)

if active_section == "Intelligence workspace" and intelligence_tool == "AI shadow mode":
    st.subheader("🧪 Controlled AI shadow mode")
    st.caption("Phase 12: an advisory model may observe a pilot case, but its output is isolated from the live workflow.")
    st.info(
        "Shadow mode compares model recommendations with the existing human workflow without changing case status, "
        "merging/deleting records, declaring environmental truth, triggering enforcement, or contacting an authority."
    )
    if not persistent or not can_shadow:
        st.info("Shadow mode is restricted to authenticated reviewer/coordinator/admin roles.")
    else:
        records = records_for_current_user()
        if not records:
            st.info("No records available for shadow evaluation.")
        else:
            selected_shadow_id = st.selectbox(
                "Observation for shadow evaluation",
                options=[r["case_id"] for r in reversed(records)],
                key="shadow_case",
            )
            selected_shadow = next(r for r in records if r["case_id"] == selected_shadow_id)
            st.caption(
                "The default adapter is local deterministic infrastructure for testing the shadow pipeline. "
                "It is not an external AI model and does not imply model performance."
            )
            if st.button("Run isolated shadow analysis", type="primary", use_container_width=True):
                # Remove prior output before retrying so failed runs fail visibly closed.
                st.session_state.pop("nema_agora_shadow_result", None)
                st.session_state.pop("nema_agora_shadow_case", None)
                try:
                    result = service.run_shadow(selected_shadow, principal)
                    st.session_state["nema_agora_shadow_result"] = result
                    st.session_state["nema_agora_shadow_case"] = selected_shadow_id
                except Exception as exc:
                    st.session_state.pop("nema_agora_shadow_result", None)
                    st.session_state.pop("nema_agora_shadow_case", None)
                    st.error("Shadow analysis could not be completed. Check access and service health, then retry.")
                    st.caption(f"Failure type: {type(exc).__name__}")

            result = st.session_state.get("nema_agora_shadow_result")
            if result and st.session_state.get("nema_agora_shadow_case") == selected_shadow_id:
                c1, c2, c3 = st.columns(3)
                c1.metric("Shadow status", result["status"])
                c2.metric("Latency", f'{result["latency_ms"]:.1f} ms')
                c3.metric("Human review", "Required")
                st.write(f"**Provider:** {result['provider']}")
                st.write(f"**Model version:** {result['model_version']}")
                if result["status"] == "SHADOW_OK" and result["output"]:
                    output = result["output"]
                    st.markdown("### Advisory output")
                    st.write(output.get("summary", "No summary supplied."))
                    st.markdown("**Category suggestions**")
                    suggestions = output.get("category_suggestions") or []
                    if suggestions:
                        st.dataframe(pd.DataFrame(suggestions), use_container_width=True, hide_index=True)
                    else:
                        st.info("No category suggestions.")
                    st.warning(output.get("decision_notice", "Human review remains mandatory."))
                else:
                    st.error(f"Shadow model failed safely: {result.get('error') or 'unknown error'}")
                st.success("Case workflow remains unchanged. This result is evaluation evidence only.")

                runs = service.list_shadow_runs(selected_shadow_id, principal)
                if runs:
                    st.markdown("### Shadow run history")
                    st.dataframe(
                        pd.DataFrame([
                            {
                                "run_id": r["run_id"],
                                "provider": r["provider"],
                                "model_version": r["model_version"],
                                "status": r["status"],
                                "latency_ms": r["latency_ms"],
                                "occurred_at": r["occurred_at"],
                            }
                            for r in runs
                        ]),
                        use_container_width=True, hide_index=True,
                    )

if active_section == "Intelligence workspace" and intelligence_tool == "Evaluation observatory":
    st.subheader("📊 Intelligence observatory")
    st.caption("Phase 11: measure reviewer feedback and evaluation readiness before considering any live model.")
    if not persistent or not can_metrics:
        st.info("The intelligence observatory is available to authenticated reviewer/coordinator/admin roles.")
    else:
        st.markdown("### Readiness gates")
        st.write("A passing snapshot means the evaluation evidence meets the pilot thresholds. It is **not** approval for production or official deployment.")
        st.info("Use the Phase 9 labelled evaluation report with the reviewer feedback trail to assess readiness.")
        st.markdown("**Current pilot gate policy**")
        st.write("- ≥25 labelled evaluation cases\n- ≥20 reviewer feedback records\n- ≥80% category accuracy\n- ≥80% duplicate F1\n- ≥90% summary faithfulness")
        st.warning("No readiness result is displayed until a versioned evaluation report is supplied. Thresholds are governance gates, not guarantees of model safety.")
if active_section == "Maps & metrics" and map_tool == "Map":
    st.subheader("Location view")
    records = records_for_current_user()
    geocoded = [
        r for r in records
        if isinstance(r.get("latitude"), (int, float)) and isinstance(r.get("longitude"), (int, float))
    ]
    if not geocoded:
        st.info("No records with coordinates yet.")
    else:
        map_df = pd.DataFrame([
            {"lat": r["latitude"], "lon": r["longitude"], "case_id": r["case_id"], "category": r["category"]}
            for r in geocoded
        ])
        st.map(map_df[["lat", "lon"]], use_container_width=True)
        st.dataframe(map_df, use_container_width=True, hide_index=True)

if active_section == "Maps & metrics" and map_tool == "Spatial evidence":
    st.subheader("Satellite-index change evidence")
    st.caption("A guided, human-reviewed NDVI/NDWI comparison with explicit quality gates.")
    st.info(
        "Live Google Earth Engine / Sentinel-2 acquisition is **not connected** in this build. "
        "No satellite imagery is fetched here. The form evaluates values you provide; the defaults are synthetic demonstration values."
    )
    with st.form("nema_agora_spatial_evidence_form"):
        st.markdown("**Scene identity and time window**")
        scene_a, scene_b = st.columns(2)
        with scene_a:
            baseline_scene = st.text_input("Baseline scene ID", value="S2-BASE-DEMO")
            baseline_date = st.date_input("Baseline acquisition date", value=date(2026, 9, 1))
        with scene_b:
            comparison_scene = st.text_input("Comparison scene ID", value="S2-COMP-DEMO")
            comparison_date = st.date_input("Comparison acquisition date", value=date(2026, 10, 1))

        st.markdown("**Index values supplied for comparison**")
        idx_a, idx_b = st.columns(2)
        with idx_a:
            baseline_ndvi = st.number_input("Baseline NDVI", min_value=-1.0, max_value=1.0, value=0.70, step=0.01, format="%.2f")
            baseline_ndwi = st.number_input("Baseline NDWI (McFeeters)", min_value=-1.0, max_value=1.0, value=0.30, step=0.01, format="%.2f")
        with idx_b:
            comparison_ndvi = st.number_input("Comparison NDVI", min_value=-1.0, max_value=1.0, value=0.50, step=0.01, format="%.2f")
            comparison_ndwi = st.number_input("Comparison NDWI (McFeeters)", min_value=-1.0, max_value=1.0, value=0.45, step=0.01, format="%.2f")

        st.markdown("**Evidence quality gates**")
        qa, qb, qc = st.columns(3)
        with qa:
            aoi_id = st.text_input("Area of interest ID", value="AOI-DEMO-UG")
            grid_id = st.text_input("Aligned grid ID", value="GRID-DEMO-10M")
            resolution_m = st.number_input("Spatial resolution (m)", min_value=0.1, max_value=10000.0, value=10.0, step=1.0)
        with qb:
            baseline_cloud = st.number_input("Baseline cloud cover (%)", min_value=0.0, max_value=100.0, value=8.0, step=1.0)
            comparison_cloud = st.number_input("Comparison cloud cover (%)", min_value=0.0, max_value=100.0, value=12.0, step=1.0)
            baseline_valid = st.number_input("Baseline valid-pixel fraction", min_value=0.0, max_value=1.0, value=0.95, step=0.01, format="%.2f")
            comparison_valid = st.number_input("Comparison valid-pixel fraction", min_value=0.0, max_value=1.0, value=0.93, step=0.01, format="%.2f")
        with qc:
            ndvi_uncertainty = st.number_input("NDVI uncertainty (index units)", min_value=0.0, max_value=1.0, value=0.03, step=0.01, format="%.2f")
            ndwi_uncertainty = st.number_input("NDWI uncertainty (index units)", min_value=0.0, max_value=1.0, value=0.04, step=0.01, format="%.2f")
            minimum_gap = st.number_input("Minimum time gap (days)", min_value=0.0, max_value=3650.0, value=7.0, step=1.0)

        st.markdown("**Candidate-review thresholds**")
        threshold_a, threshold_b, threshold_c = st.columns(3)
        with threshold_a:
            ndvi_threshold = st.number_input("Minimum absolute NDVI delta", min_value=0.0, max_value=2.0, value=0.15, step=0.01, format="%.2f")
        with threshold_b:
            ndwi_threshold = st.number_input("Minimum absolute NDWI delta", min_value=0.0, max_value=2.0, value=0.15, step=0.01, format="%.2f")
        with threshold_c:
            rule_mode = st.selectbox("Detection rule", ["ANY", "ALL", "WEIGHTED"], index=0)
        submitted = st.form_submit_button("Evaluate change evidence", type="primary", use_container_width=True)

    if submitted:
        st.session_state.pop("nema_agora_spatial_evidence_bundle", None)
        baseline_timestamp = f"{baseline_date.isoformat()}T10:00:00+00:00"
        comparison_timestamp = f"{comparison_date.isoformat()}T10:00:00+00:00"
        change_evidence = spatial_temporal_change_evidence(
            baseline_scene_id=baseline_scene.strip(),
            comparison_scene_id=comparison_scene.strip(),
            baseline_acquired_at=baseline_timestamp,
            comparison_acquired_at=comparison_timestamp,
            baseline_indices={"NDVI": baseline_ndvi, "NDWI_MCFEETERS": baseline_ndwi},
            comparison_indices={"NDVI": comparison_ndvi, "NDWI_MCFEETERS": comparison_ndwi},
            min_temporal_gap_days=minimum_gap,
        )
        if change_evidence.get("state") != "CANDIDATE_CHANGE_EVIDENCE":
            st.error("Change calculation was blocked by input validation.")
            st.json(change_evidence.get("findings", []))
        else:
            quality_evidence = spatial_temporal_quality_evidence(
                change_evidence=change_evidence,
                baseline_aoi_id=aoi_id.strip(),
                comparison_aoi_id=aoi_id.strip(),
                baseline_grid_id=grid_id.strip(),
                comparison_grid_id=grid_id.strip(),
                spatial_alignment="ALIGNED",
                spatial_resolution_m=resolution_m,
                baseline_cloud_cover_pct=baseline_cloud,
                comparison_cloud_cover_pct=comparison_cloud,
                baseline_valid_fraction=baseline_valid,
                comparison_valid_fraction=comparison_valid,
                ndvi_uncertainty=ndvi_uncertainty,
                ndwi_uncertainty=ndwi_uncertainty,
            )
            if quality_evidence.get("state") != "CANDIDATE_CHANGE_EVIDENCE":
                st.error("Quality gates blocked candidate scoring. Review the findings before continuing.")
                st.json(quality_evidence.get("findings", []))
            else:
                candidate = detect_candidate(
                    quality_evidence=quality_evidence,
                    min_abs_ndvi_delta=ndvi_threshold,
                    min_abs_ndwi_delta=ndwi_threshold,
                    rule_mode=rule_mode,
                )
                if candidate.get("state") == "CONTROL_REQUIRED":
                    st.error("Candidate scoring was blocked by validation.")
                    st.json(candidate.get("findings", []))
                else:
                    try:
                        bundle = build_spatial_evidence_bundle(
                            change_evidence=change_evidence,
                            quality_evidence=quality_evidence,
                            candidate=candidate,
                        )
                    except (ValueError, TypeError) as exc:
                        st.session_state.pop("nema_agora_spatial_evidence_bundle", None)
                        st.error("Spatial evidence could not be bundled safely. Review the validation findings and correct the inputs.")
                        st.caption(str(exc))
                    else:
                        st.session_state["nema_agora_spatial_evidence_bundle"] = bundle

    evidence_bundle = st.session_state.get("nema_agora_spatial_evidence_bundle")
    bundle_validation = validate_spatial_evidence_bundle(evidence_bundle) if isinstance(evidence_bundle, dict) else None
    if isinstance(evidence_bundle, dict) and bundle_validation and not bundle_validation["valid"]:
        st.error("Spatial evidence bundle integrity check failed; export is disabled.")
        st.json(bundle_validation["findings"])
    if isinstance(evidence_bundle, dict) and bundle_validation and bundle_validation["valid"]:
        change_evidence = evidence_bundle["change_evidence"]
        candidate = evidence_bundle["candidate"]
        delta_ndvi = change_evidence["change"]["NDVI"]["delta"]
        delta_ndwi = change_evidence["change"]["NDWI_MCFEETERS"]["delta"]
        m1, m2, m3 = st.columns(3)
        m1.metric("NDVI delta", f"{delta_ndvi:+.3f}")
        m2.metric("NDWI delta", f"{delta_ndwi:+.3f}")
        m3.metric("Candidate status", candidate["state"].replace("_", " ").title())
        st.markdown("### How to read these values")
        st.caption(
            "Delta = comparison value minus baseline value. These are index differences, not percentages "
            "of land or water changed. The values entered above are not fetched from satellite imagery."
        )
        interpretation_cols = st.columns(2)
        with interpretation_cols[0]:
            if delta_ndvi < 0:
                st.write("**NDVI decreased:** the supplied vegetation-index value is lower in the comparison input.")
            elif delta_ndvi > 0:
                st.write("**NDVI increased:** the supplied vegetation-index value is higher in the comparison input.")
            else:
                st.write("**NDVI unchanged:** the two supplied NDVI values are equal.")
        with interpretation_cols[1]:
            if delta_ndwi < 0:
                st.write("**NDWI decreased:** the supplied water-related index value is lower in the comparison input.")
            elif delta_ndwi > 0:
                st.write("**NDWI increased:** the supplied water-related index value is higher in the comparison input.")
            else:
                st.write("**NDWI unchanged:** the two supplied NDWI values are equal.")
        st.warning(
            "Index direction alone does not establish the cause, extent, or legal significance of a change. "
            "Check scene dates, cloud and valid-pixel quality, spatial alignment, seasonality, and independent field evidence."
        )
        if candidate["state"] == "CANDIDATE_CHANGE_DETECTED":
            st.warning(
                "A change signal crossed the selected thresholds. This is a review candidate, "
                "not a verified environmental change, legal finding, or enforcement instruction."
            )
        else:
            st.info(
                "No threshold was crossed under this policy. That does not prove that no environmental change occurred."
            )
        with st.expander("Inspect evidence, quality gates and fingerprints"):
            st.json(evidence_bundle)
        download_col, clear_col = st.columns([3, 1])
        with download_col:
            st.download_button(
                "Export spatial evidence JSON",
                data=json.dumps(evidence_bundle, ensure_ascii=False, sort_keys=True, indent=2),
                file_name="nema-agora-spatial-evidence.json",
                mime="application/json",
                use_container_width=True,
            )
        with clear_col:
            if st.button("Clear result", key="nema_agora_clear_spatial_result", use_container_width=True):
                st.session_state.pop("nema_agora_spatial_evidence_bundle", None)
                st.rerun()


if active_section == "Maps & metrics" and map_tool == "Data sources & asset receipts":
    st.subheader("Data source register & asset provenance")
    st.caption("A practical bridge between public source references and reproducible evidence handling.")
    st.info(
        "The catalogue below is reference-only. This workspace does not fetch Sentinel-2 scenes or connect to government portals. "
        "Uploaded files are hashed in this Streamlit session; this tool does not persist the file bytes or verify their authenticity."
    )
    sources = list_sources()
    source_frame = pd.DataFrame([
        {
            "Source ID": item["source_id"],
            "Publisher": item["publisher"],
            "Reference": item["title"],
            "Type": item["source_type"],
            "Integration": item["integration_status"],
            "Machine endpoint verified": item["machine_endpoint_verified"],
            "Automated ingestion": item["automated_ingestion_enabled"],
        }
        for item in sources
    ])
    st.dataframe(source_frame, use_container_width=True, hide_index=True)
    with st.expander("Source limitations and official references"):
        for item in sources:
            st.markdown(f"**{item['title']}** — [{item['publisher']}]({item['url']})")
            st.caption(item["intended_use"])
            st.caption("Limitations: " + "; ".join(item["limitations"]))
    st.markdown("### Validate an area of interest (AOI)")
    st.caption(
        "Upload a GeoJSON polygon or multipolygon to check basic structure and WGS84 coordinate bounds before a monitoring study. "
        "This does not validate legal boundaries, geometry topology, or positional accuracy."
    )
    aoi_file = st.file_uploader(
        "GeoJSON AOI file",
        type=["geojson", "json"],
        accept_multiple_files=False,
        key="nema_agora_aoi_upload",
    )
    if st.button("Validate AOI file", key="nema_agora_validate_aoi", use_container_width=True):
        st.session_state.pop("nema_agora_aoi_report", None)
        if aoi_file is None:
            st.error("Choose a GeoJSON file first.")
        else:
            try:
                aoi_document = json.loads(aoi_file.getvalue().decode("utf-8"))
                aoi_report = validate_geojson_aoi(aoi_document)
            except (UnicodeDecodeError, json.JSONDecodeError):
                aoi_report = {"valid": False, "findings": [{"code": "INVALID_JSON_OR_UTF8"}]}
            st.session_state["nema_agora_aoi_report"] = {
                "filename": aoi_file.name,
                "report": aoi_report,
            }
    aoi_result = st.session_state.get("nema_agora_aoi_report")
    if isinstance(aoi_result, dict):
        aoi_report = aoi_result["report"]
        st.write(f"**AOI validation:** {'BASIC STRUCTURE VALID' if aoi_report['valid'] else 'CONTROL REQUIRED'}")
        st.caption(f"File: {aoi_result['filename']}")
        if aoi_report.get("bounds"):
            st.json(aoi_report["bounds"])
        if aoi_report.get("findings"):
            st.dataframe(pd.DataFrame(aoi_report["findings"]), use_container_width=True, hide_index=True)
        st.warning("Basic GeoJSON validation is not proof that this AOI matches an official wetland or protected-area boundary.")
        st.download_button(
            "Download AOI validation report",
            data=json.dumps(aoi_result, ensure_ascii=False, sort_keys=True, indent=2),
            file_name="nema-agora-aoi-validation.json",
            mime="application/json",
            key="nema_agora_download_aoi_report",
            use_container_width=True,
        )

    st.markdown("### Ingest real GeoTIFF scenes")
    st.caption(
        "Optional rasterio-backed path: upload one multiband GeoTIFF and one same-grid valid-pixel mask GeoTIFF for each date. "
        "The first three bands must be ordered B03, B04, B08. The mask must use 1 for valid and 0 for invalid pixels."
    )
    st.warning(
        "The cloud/shadow mask assertion is provided by the uploader and is not independently verified. "
        "Only EPSG:4326, north-up unrotated grids up to 250,000 pixels are accepted. No reprojection or resampling is performed."
    )
    with st.expander("GeoTIFF pair upload and processing", expanded=False):
        base_raster = st.file_uploader("Baseline multiband GeoTIFF", type=["tif", "tiff"], key="nema_geotiff_base")
        base_mask = st.file_uploader("Baseline valid-pixel mask GeoTIFF", type=["tif", "tiff"], key="nema_geotiff_base_mask")
        comp_raster = st.file_uploader("Comparison multiband GeoTIFF", type=["tif", "tiff"], key="nema_geotiff_comp")
        comp_mask = st.file_uploader("Comparison valid-pixel mask GeoTIFF", type=["tif", "tiff"], key="nema_geotiff_comp_mask")
        aoi_geojson_file = st.file_uploader(
            "Monitoring AOI boundary (GeoJSON; Polygon/MultiPolygon)",
            type=["geojson", "json"], key="nema_geotiff_aoi_geojson",
            help="The same boundary is applied to both scenes using pixel-center inclusion. Use a boundary whose authority and coordinate accuracy you have checked.",
        )
        gi1, gi2, gi3 = st.columns(3)
        with gi1:
            base_scene_id = st.text_input("Baseline scene ID", value="BASELINE-001", key="nema_geotiff_base_id")
            base_acquired = st.text_input("Baseline acquisition timestamp (timezone required)", value="2026-06-01T10:00:00Z", key="nema_geotiff_base_time")
        with gi2:
            comp_scene_id = st.text_input("Comparison scene ID", value="COMPARISON-001", key="nema_geotiff_comp_id")
            comp_acquired = st.text_input("Comparison acquisition timestamp (timezone required)", value="2026-09-01T10:00:00Z", key="nema_geotiff_comp_time")
        with gi3:
            raster_aoi_id = st.text_input("AOI ID", value="PILOT-AOI-001", key="nema_geotiff_aoi")
            scale = st.number_input("Reflectance scale multiplier", min_value=0.00000001, max_value=1.0, value=0.0001, format="%.8f", key="nema_geotiff_scale")
            offset = st.number_input("Reflectance offset", min_value=-1.0, max_value=1.0, value=0.0, format="%.6f", key="nema_geotiff_offset")
        mask_assertion = st.checkbox(
            "I have applied a documented cloud/shadow validity mask to both mask files",
            value=False, key="nema_geotiff_mask_assertion",
        )
        if st.button("Ingest GeoTIFF pair and calculate indices", key="nema_geotiff_process", type="primary", use_container_width=True):
            st.session_state.pop("nema_agora_geotiff_analysis", None)
            if not all((base_raster, base_mask, comp_raster, comp_mask, aoi_geojson_file)):
                st.error("Upload both raster files, both valid-pixel masks, and the AOI GeoJSON boundary.")
            elif not mask_assertion:
                st.error("Confirm the cloud/shadow mask workflow before processing.")
            else:
                try:
                    aoi_geojson = json.loads(aoi_geojson_file.getvalue().decode("utf-8"))
                    base_scene = read_geotiff_scene(
                        raster_bytes=base_raster.getvalue(), valid_mask_bytes=base_mask.getvalue(),
                        scene_id=base_scene_id, acquired_at=base_acquired, aoi_id=raster_aoi_id,
                        reflectance_scale=scale, reflectance_offset=offset,
                        cloud_shadow_mask_applied=mask_assertion,
                        aoi_geojson=aoi_geojson,
                    )
                    comp_scene = read_geotiff_scene(
                        raster_bytes=comp_raster.getvalue(), valid_mask_bytes=comp_mask.getvalue(),
                        scene_id=comp_scene_id, acquired_at=comp_acquired, aoi_id=raster_aoi_id,
                        reflectance_scale=scale, reflectance_offset=offset,
                        cloud_shadow_mask_applied=mask_assertion,
                        aoi_geojson=aoi_geojson,
                    )
                    geo_result = analyze_paired_raster_arrays(
                        baseline_scene=base_scene, comparison_scene=comp_scene,
                    )
                    geo_result["ingestion"] = {
                        "baseline": base_scene["ingestion"],
                        "comparison": comp_scene["ingestion"],
                    }
                    fingerprint_payload = dict(geo_result)
                    fingerprint_payload.pop("fingerprint", None)
                    geo_result["fingerprint"] = hashlib.sha256(
                        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
                    ).hexdigest()
                    st.session_state["nema_agora_geotiff_analysis"] = geo_result
                except (ValueError, RuntimeError, TypeError) as exc:
                    st.error("GeoTIFF ingestion stopped. Check the input contract and optional raster dependency.")
                    st.caption(str(exc))
        geo_result = st.session_state.get("nema_agora_geotiff_analysis")
        if isinstance(geo_result, dict):
            if geo_result.get("state") == "PIXEL_ANALYSIS_COMPLETE" and validate_paired_array_analysis(geo_result)["valid"]:
                st.success("GeoTIFF pair processed and analysis integrity validated.")
                st.json({key: value for key, value in geo_result.items() if key != "pixel_arrays"})
                st.download_button(
                    "Download GeoTIFF analysis evidence JSON",
                    data=json.dumps(geo_result, sort_keys=True, ensure_ascii=False, indent=2),
                    file_name="nema-agora-geotiff-analysis.json", mime="application/json",
                    key="nema_geotiff_download", use_container_width=True,
                )
            else:
                st.error("GeoTIFF analysis did not pass quality or integrity checks.")
                st.json(geo_result.get("findings", []))

    st.markdown("### Run paired-scene pixel analysis")
    st.caption(
        "Upload two JSON scene cubes containing decoded normalized reflectance arrays for B03, B04 and B08, "
        "a boolean valid-pixel mask, acquisition metadata and a declared cloud-mask status. "
        "This performs pixelwise NDVI and McFeeters NDWI calculations on aligned arrays; it does not read GeoTIFF files or fetch satellite data."
    )
    st.info(
        "Input contract: each scene JSON must contain scene_id, acquired_at (timezone-aware), aoi_id, grid_id, "
        "crs='EPSG:4326', bands with same-shaped 2D B03/B04/B08 arrays scaled to 0..1, valid_mask (boolean 2D array), "
        "and cloud_mask_applied=true. For safety, each scene is limited to 250,000 pixels."
    )
    cube_left, cube_right = st.columns(2)
    with cube_left:
        baseline_cube_file = st.file_uploader(
            "Baseline scene cube JSON", type=["json"], accept_multiple_files=False,
            key="nema_agora_baseline_cube_json",
        )
    with cube_right:
        comparison_cube_file = st.file_uploader(
            "Comparison scene cube JSON", type=["json"], accept_multiple_files=False,
            key="nema_agora_comparison_cube_json",
        )
    q1, q2, q3 = st.columns(3)
    with q1:
        min_valid_fraction = st.slider(
            "Minimum valid fraction", min_value=0.1, max_value=1.0, value=0.7, step=0.05,
            key="nema_agora_array_min_valid_fraction",
        )
    with q2:
        min_ndvi_delta = st.slider(
            "Absolute NDVI delta threshold", min_value=0.0, max_value=1.0, value=0.15, step=0.05,
            key="nema_agora_array_min_ndvi_delta",
        )
    with q3:
        min_ndwi_delta = st.slider(
            "Absolute NDWI delta threshold", min_value=0.0, max_value=1.0, value=0.15, step=0.05,
            key="nema_agora_array_min_ndwi_delta",
        )
    if st.button("Calculate pixel-level NDVI / NDWI deltas", key="nema_agora_run_array_analysis", type="primary", use_container_width=True):
        st.session_state.pop("nema_agora_paired_array_analysis", None)
        if not baseline_cube_file or not comparison_cube_file:
            st.error("Upload both baseline and comparison scene cube JSON files.")
        else:
            try:
                baseline_cube = json.loads(baseline_cube_file.getvalue().decode("utf-8"))
                comparison_cube = json.loads(comparison_cube_file.getvalue().decode("utf-8"))
                analysis_result = analyze_paired_raster_arrays(
                    baseline_scene=baseline_cube,
                    comparison_scene=comparison_cube,
                    min_valid_fraction=min_valid_fraction,
                    min_abs_ndvi_delta=min_ndvi_delta,
                    min_abs_ndwi_delta=min_ndwi_delta,
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
                st.error("Pixel analysis could not run. Check the scene-cube JSON contract.")
                st.caption(str(exc))
            else:
                st.session_state["nema_agora_paired_array_analysis"] = analysis_result
    array_result = st.session_state.get("nema_agora_paired_array_analysis")
    if isinstance(array_result, dict):
        array_integrity = validate_paired_array_analysis(array_result)
        if array_result.get("state") == "PIXEL_ANALYSIS_COMPLETE" and array_integrity["valid"]:
            st.success("Pixel-level analysis completed on the uploaded arrays.")
            metrics = st.columns(4)
            metrics[0].metric("Joint valid pixels", array_result["quality"]["joint_valid_pixels"])
            metrics[1].metric("Joint valid fraction", f"{array_result['quality']['joint_valid_fraction']:.1%}")
            metrics[2].metric("Mean NDVI delta", array_result["summary"]["NDVI"]["mean"])
            metrics[3].metric("Mean NDWI delta", array_result["summary"]["NDWI_MCFEETERS"]["mean"])
            st.caption("These are spectral screening statistics, not proof of environmental change or a legal conclusion.")
            with st.expander("Inspect summary and pixel arrays"):
                st.json({key: value for key, value in array_result.items() if key != "pixel_arrays"})
                st.json(array_result["pixel_arrays"])
            st.download_button(
                "Download pixel analysis evidence JSON",
                data=json.dumps(array_result, sort_keys=True, ensure_ascii=False, indent=2),
                file_name="nema-agora-paired-pixel-analysis.json",
                mime="application/json",
                key="nema_agora_download_array_analysis",
                use_container_width=True,
            )
        else:
            st.error("Pixel analysis is not exportable: input/quality controls or output integrity validation failed.")
            st.json(array_result.get("findings", array_integrity.get("findings", [])))

    st.markdown("### Assemble a paired-scene study manifest")
    st.caption(
        "Combine a baseline receipt, a later comparison receipt and the AOI file into a reproducible study plan. "
        "This does not calculate NDVI/NDWI or perform raster change analysis."
    )
    manifest_a, manifest_b = st.columns(2)
    with manifest_a:
        baseline_receipt_file = st.file_uploader(
            "Baseline receipt JSON", type=["json"], accept_multiple_files=False,
            key="nema_agora_baseline_receipt_json",
        )
    with manifest_b:
        comparison_receipt_file = st.file_uploader(
            "Comparison receipt JSON", type=["json"], accept_multiple_files=False,
            key="nema_agora_comparison_receipt_json",
        )
    manifest_aoi_file = st.file_uploader(
        "AOI GeoJSON for this study", type=["geojson", "json"],
        accept_multiple_files=False, key="nema_agora_manifest_aoi_json",
    )
    study_id = st.text_input("Study ID", value="WETLAND-PILOT-001", key="nema_agora_study_id")
    processing_notes = st.text_area(
        "Processing and comparability checks still required",
        value="Verify scene products, acquisition metadata, cloud masks, CRS/grid alignment, seasonality and field references before any change analysis.",
        max_chars=2000, key="nema_agora_study_processing_notes",
    )
    if st.button("Build paired-scene study manifest", key="nema_agora_build_study_manifest", type="primary", use_container_width=True):
        st.session_state.pop("nema_agora_paired_study_manifest", None)
        if not baseline_receipt_file or not comparison_receipt_file or not manifest_aoi_file:
            st.error("Provide both receipt JSON files and the AOI GeoJSON.")
        else:
            try:
                baseline_json = json.loads(baseline_receipt_file.getvalue().decode("utf-8"))
                comparison_json = json.loads(comparison_receipt_file.getvalue().decode("utf-8"))
                aoi_json = json.loads(manifest_aoi_file.getvalue().decode("utf-8"))
                manifest = build_paired_study_manifest(
                    study_id=study_id,
                    aoi_document=aoi_json,
                    baseline_receipt=baseline_json,
                    comparison_receipt=comparison_json,
                    processing_notes=processing_notes,
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
                st.error("Study manifest was not created. Correct the inputs and retry.")
                st.caption(str(exc))
            else:
                st.session_state["nema_agora_paired_study_manifest"] = manifest
                st.success("Paired-scene study manifest created and validated in this session.")
    study_manifest = st.session_state.get("nema_agora_paired_study_manifest")
    if isinstance(study_manifest, dict):
        manifest_report = validate_paired_study_manifest(study_manifest)
        st.write(f"**Manifest integrity:** {'VALID' if manifest_report['valid'] else 'CONTROL REQUIRED'}")
        st.write(f"**Study state:** {study_manifest.get('study_state')}")
        st.write(f"**Fingerprint:** {study_manifest.get('fingerprint')}")
        st.warning(
            "READY FOR PROCESSING REVIEW is not a finding of environmental change. "
            "Provider connection, raster processing, change analysis and official-boundary verification remain unclaimed."
        )
        if manifest_report["valid"]:
            st.download_button(
                "Download paired-scene study manifest",
                data=json.dumps(study_manifest, sort_keys=True, ensure_ascii=False, indent=2),
                file_name=f"{study_manifest['study_id']}-manifest.json",
                mime="application/json",
                key="nema_agora_download_study_manifest",
                use_container_width=True,
            )
        else:
            st.error("Manifest integrity failed; export is disabled.")
            st.json(manifest_report["findings"])

    st.markdown("### Create a manual asset receipt")
    st.caption(
        "Use this for a file you already have permission to use. The receipt records metadata and checksums, "
        "not proof that the file is authentic or scientifically suitable."
    )
    uploaded_assets = st.file_uploader(
        "Choose source assets to fingerprint",
        type=["tif", "tiff", "jp2", "geojson", "json", "zip", "csv"],
        accept_multiple_files=True,
        key="nema_agora_receipt_uploads",
        help="Files are read in the current session to calculate SHA-256 checksums. This feature does not upload them to a permanent store.",
    )
    source_options = {item["source_id"]: item for item in sources}
    source_id = st.selectbox(
        "Source reference",
        options=list(source_options),
        format_func=lambda value: f"{value} — {source_options[value]['title']}",
        key="nema_agora_receipt_source",
    )
    receipt_a, receipt_b = st.columns(2)
    with receipt_a:
        receipt_id = st.text_input("Receipt ID", value="PILOT-ASSET-001", key="nema_agora_receipt_id")
        receipt_aoi = st.text_input("AOI ID", value="PILOT-AOI-001", key="nema_agora_receipt_aoi")
        acquired_date = st.date_input("Asset acquisition date", value=date.today(), key="nema_agora_receipt_acquired")
        asset_role = st.selectbox("Scene role", ["baseline", "comparison", "context"], key="nema_agora_receipt_role")
    with receipt_b:
        receipt_crs = st.text_input("Coordinate reference system (CRS)", value="EPSG:32636", key="nema_agora_receipt_crs")
        receipt_resolution = st.number_input("Spatial resolution (metres)", min_value=0.1, max_value=10000.0, value=10.0, key="nema_agora_receipt_resolution")
        receipt_cloud = st.number_input("Cloud cover (%)", min_value=0.0, max_value=100.0, value=0.0, key="nema_agora_receipt_cloud")
        receipt_valid = st.number_input("Valid-pixel fraction (0–1)", min_value=0.0, max_value=1.0, value=1.0, step=0.01, key="nema_agora_receipt_valid")
    receipt_limitations = st.text_area(
        "Limitations and verification still needed",
        value="Source authenticity, licence, scene metadata and scientific suitability require independent verification.",
        max_chars=1500,
        key="nema_agora_receipt_limitations",
    )
    if st.button("Build and validate manual receipt", type="primary", use_container_width=True, key="nema_agora_build_receipt"):
        st.session_state.pop("nema_agora_manual_asset_receipt", None)
        if not uploaded_assets:
            st.error("Upload at least one asset before building a receipt.")
        else:
            asset_records = []
            for index, uploaded in enumerate(uploaded_assets, start=1):
                raw = uploaded.getvalue()
                safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in uploaded.name)[:100]
                asset_records.append({
                    "asset_id": f"ASSET-{index:03d}-{safe_name}",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "storage_ref": f"session-upload://{index:03d}/{safe_name}",
                    "media_type": uploaded.type or "application/octet-stream",
                })
            try:
                receipt = build_manual_asset_receipt(
                    receipt_id=receipt_id.strip(),
                    source_id=source_id,
                    acquired_at=f"{acquired_date.isoformat()}T00:00:00+00:00",
                    recorded_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    aoi_id=receipt_aoi.strip(),
                    baseline_or_comparison=asset_role,
                    crs=receipt_crs.strip(),
                    spatial_resolution_m=receipt_resolution,
                    cloud_cover_pct=receipt_cloud,
                    valid_pixel_fraction=receipt_valid,
                    assets=asset_records,
                    limitations=[line.strip() for line in receipt_limitations.splitlines() if line.strip()],
                )
            except (ValueError, TypeError) as exc:
                st.error("Receipt validation failed. Correct the metadata and retry.")
                st.caption(str(exc))
            else:
                st.session_state["nema_agora_manual_asset_receipt"] = receipt
                st.success("Manual asset receipt created and validated in this session.")
    receipt = st.session_state.get("nema_agora_manual_asset_receipt")
    if isinstance(receipt, dict):
        report = validate_asset_receipt(receipt)
        st.write(f"**Receipt integrity:** {'VALID' if report['valid'] else 'INVALID'}")
        st.write(f"**Fingerprint:** {receipt['fingerprint']}")
        st.caption("A valid fingerprint detects later metadata changes; it does not independently verify source authenticity.")
        if report["valid"]:
            st.download_button(
                "Download manual asset receipt (JSON)",
                data=json.dumps(receipt, sort_keys=True, ensure_ascii=False, indent=2),
                file_name=f"{receipt['receipt_id']}.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.error("Receipt integrity check failed; export is disabled.")
            st.json(report["findings"])

if active_section == "Maps & metrics" and map_tool == "Pilot metrics":
    st.subheader("Pilot monitoring snapshot")
    if persistent and not can_metrics:
        st.info("Metrics are restricted to reviewer/coordinator/admin roles.")
    else:
        records = records_for_current_user()
        total = len(records)
        reviewed = sum(1 for r in records if r["status"] != "Received")
        closed = sum(1 for r in records if r["status"] == "Closed")
        m1, m2, m3 = st.columns(3)
        m1.metric("Visible records", total)
        m2.metric("Reviewed / progressed", reviewed)
        m3.metric("Closed", closed)
        if records:
            counts = pd.DataFrame(records)["status"].value_counts().rename_axis("status").reset_index(name="count")
            st.bar_chart(counts.set_index("status"))
        st.warning("Prototype metrics are not verified environmental outcomes or official response statistics.")


if active_section == "Governance & help" and governance_tool == "Release readiness":
    st.subheader("Release readiness — evidence completeness")
    st.caption("One-page workspace • exact-commit evidence • fail-closed review")
    if not persistent or principal is None or not principal.is_authorised:
        st.info("Release-readiness review requires an authenticated, server-provisioned account.")
    elif not has_permission(principal.role, "intelligence:pilot_readiness"):
        st.info("Your role is not permitted to inspect release-readiness evidence.")
    else:
        st.warning(
            "This checks evidence completeness for human release review only. It does not deploy the app, "
            "approve production, submit reports to NEMA, or authorize environmental, regulatory, enforcement, "
            "or emergency action."
        )
        gate_names = [
            "focused_ci",
            "clean_environment_end_to_end",
            "role_and_security_verification",
            "backup_restore_verification",
            "retention_verification",
            "evaluation_artifact_verification",
            "accessibility_and_data_governance_review",
            "institutional_approval",
        ]
        evidence_template = {
            gate: {
                "status": "PENDING",
                "evidence_ref": "",
                "evidence_sha256": "",
                "verified_at": "",
                "candidate_sha": "",
            }
            for gate in gate_names
        }
        with st.expander("Evidence JSON template", expanded=False):
            st.code(json.dumps(evidence_template, indent=2), language="json")
            st.download_button(
                "Download evidence template",
                data=json.dumps(evidence_template, indent=2),
                file_name="nema_agora_release_evidence_template.json",
                mime="application/json",
                key="nema_agora_release_template_download",
            )
        candidate_sha = st.text_input(
            "Release candidate Git SHA (40 or 64 hexadecimal characters)",
            key="nema_agora_candidate_sha",
        )
        observed_at = st.text_input(
            "Assessment time (ISO 8601 with timezone)",
            value=datetime.now(timezone.utc).isoformat(),
            key="nema_agora_readiness_observed_at",
        )
        evidence_json = st.text_area(
            "Release evidence JSON",
            value=json.dumps(evidence_template, indent=2),
            height=300,
            help="Every gate needs PASS, an evidence reference, a SHA-256 digest, a timezone-aware verification time, and the exact candidate SHA.",
            key="nema_agora_readiness_evidence_json",
        )
        if st.button("Evaluate release readiness", type="primary", key="nema_agora_evaluate_readiness"):
            try:
                evidence = json.loads(evidence_json)
                report = evaluate_release_readiness(
                    candidate_sha=candidate_sha.strip(),
                    evidence=evidence,
                    observed_at=observed_at.strip(),
                )
                validate_release_readiness_report(report)
                if report["decision"] == "READY_FOR_HUMAN_RELEASE_REVIEW":
                    st.success(report["decision"])
                else:
                    st.error(report["decision"])
                left, middle, right = st.columns(3)
                left.metric("Passed gates", f"{report['passed_gate_count']}/{report['gate_count']}")
                middle.metric("Findings", len(report["findings"]))
                right.metric("Execution gate", report["execution_gate"])
                st.subheader("Gate results")
                st.dataframe(
                    [{"gate": gate, "passed": passed} for gate, passed in report["gates"].items()],
                    use_container_width=True,
                    hide_index=True,
                )
                if report["findings"]:
                    st.subheader("Findings requiring attention")
                    st.dataframe(report["findings"], use_container_width=True, hide_index=True)
                st.subheader("Fingerprint-bound report")
                st.json(report)
                st.download_button(
                    "Download readiness report",
                    data=json.dumps(report, sort_keys=True, indent=2),
                    file_name="nema_agora_release_readiness.json",
                    mime="application/json",
                    key="nema_agora_readiness_report_download",
                )
            except Exception as exc:
                st.error(
                    "Readiness could not be evaluated. Check the candidate SHA and evidence JSON, "
                    "then retry. No release approval was granted."
                )
                st.caption(f"Failure type: {type(exc).__name__}")
        st.caption(
            "A positive result means READY_FOR_HUMAN_RELEASE_REVIEW only. It is not production approval; "
            "independent human review and institutional approval remain required."
        )


if active_section == "Governance & help" and governance_tool == "Operations & backups":
    st.subheader("Operations & backups")
    st.caption("Operational controls for the configured SQLite pilot database.")
    if mode != "persistent" or not persistent or principal is None or principal.role != "admin":
        st.info("Backup operations require persistent mode and an authenticated, server-provisioned admin role.")
    else:
        database_path = database_path_from_secrets(st.secrets)
        backup_dir = backup_dir_from_secrets(st.secrets)
        retention = backup_retention_from_secrets(st.secrets)
        if database_path is None:
            st.error("Configure nema_agora.database_path before using operational controls.")
        elif backup_dir is None:
            st.error("Configure nema_agora.backup_dir to a durable, server-managed directory before creating backups.")
        elif retention is None:
            st.error("nema_agora.backup_retention must be an integer from 1 to 3650.")
        else:
            st.warning(
                "Backups may contain environmental case records. Store them on a restricted, durable server volume; "
                "do not use a temporary filesystem as the only recovery copy."
            )
            db_exists = database_path.is_file()
            db_healthy = integrity_check(database_path) if db_exists else False
            left, middle, right = st.columns(3)
            left.metric("Database file", "Present" if db_exists else "Missing")
            middle.metric("SQLite integrity", "OK" if db_healthy else "NOT VERIFIED")
            right.metric("Retention target", f"{retention} backups")
            if not db_exists:
                st.error("The configured database file does not exist. No backup was attempted.")
            elif not db_healthy:
                st.error("Database integrity check failed. Creating a backup is blocked.")
            elif st.button("Create verified backup", type="primary", key="nema_agora_create_backup"):
                try:
                    created_backup = backup_database(database_path, backup_dir)
                except Exception as exc:
                    st.error("Backup creation failed. Check server filesystem permissions and database health.")
                    st.caption(f"Failure type: {type(exc).__name__}")
                else:
                    st.success(f"Backup created and integrity-checked: {created_backup.name}")
                    st.rerun()
            backups = list_backups(backup_dir)
            st.markdown("**Available backups**")
            if backups:
                st.dataframe(
                    [{"filename": p.name, "size_bytes": p.stat().st_size,
                      "integrity": "OK" if integrity_check(p) else "FAILED"}
                     for p in backups],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No recognised backups found in the configured backup directory.")
            healthy_backups = [p for p in backups if integrity_check(p)]
            st.markdown("**Restore from a verified backup**")
            if not healthy_backups:
                st.info("Restore is unavailable until at least one recognised backup passes integrity checks.")
            elif not db_exists or not db_healthy:
                st.error("Restore is blocked because the current target database is missing or unhealthy; use the documented recovery procedure.")
            else:
                selected_backup_name = st.selectbox(
                    "Verified backup",
                    options=[p.name for p in healthy_backups],
                    key="nema_agora_restore_backup_choice",
                )
                st.warning(
                    "Restore replaces the current database contents. A pre-restore backup will be attempted first. "
                    "Coordinate a maintenance window so no other process writes to the database during recovery."
                )
                confirm_restore = st.checkbox(
                    "I understand this replaces current database contents.",
                    key="nema_agora_restore_confirm_checkbox",
                )
                typed_confirmation = st.text_input(
                    'Type RESTORE DATABASE to enable restore',
                    key="nema_agora_restore_confirm_text",
                )
                if st.button(
                    "Restore selected backup",
                    disabled=not (confirm_restore and typed_confirmation == "RESTORE DATABASE"),
                    key="nema_agora_restore_execute",
                ):
                    source_backup = backup_dir / selected_backup_name
                    try:
                        # Keep a verified copy of the current database before destructive replacement.
                        pre_restore_backup = backup_database(database_path, backup_dir)
                        restore_database(
                            source_backup,
                            database_path,
                            confirm_destructive=True,
                        )
                    except Exception as exc:
                        st.error(
                            "Restore did not complete successfully. Do not resume normal operations until database integrity and records are checked."
                        )
                        st.caption(f"Failure type: {type(exc).__name__}")
                    else:
                        st.success(
                            f"Restore completed from {source_backup.name}. Pre-restore backup retained as {pre_restore_backup.name}."
                        )
                        st.rerun()

            if len(backups) > retention:
                st.warning(f"{len(backups) - retention} backup(s) exceed the configured retention target.")
                if st.button("Apply backup retention", key="nema_agora_apply_retention"):
                    try:
                        removed = prune_backups(backup_dir, keep=retention)
                    except Exception as exc:
                        st.error("Retention cleanup failed. No successful cleanup is claimed.")
                        st.caption(f"Failure type: {type(exc).__name__}")
                    else:
                        st.success(f"Retention cleanup removed {len(removed)} older backup(s).")
                        st.rerun()
            st.caption(
                "This panel creates and checks backups on the configured server filesystem. "
                "It does not prove off-site recovery, restore readiness, encryption, or disaster-recovery compliance."
            )

if active_section == "Governance & help" and governance_tool == "About the pilot":
    st.subheader("Project purpose")
    st.write(
        "NEMA-AGORA is a proposed student-led pilot for organising environmental observations, "
        "review status, location information and evaluation data. It is designed to complement "
        "existing environmental-management systems, not replace them."
    )
    st.markdown("**What this pilot supports**")
    st.markdown(
        "- Capture structured environmental observations and track review status\n"
        "- Run advisory evidence and quality checks on supplied values\n"
        "- Keep a traceable record of reviewer decisions and authorised exports\n"
        "- View pilot activity and candidate spatial-change signals"
    )
    st.markdown("**Security and human oversight**")
    st.markdown(
        "- Persistent records require authenticated, server-provisioned roles\n"
        "- Submitters are restricted to their own records; review, audit and export are permission-gated\n"
        "- AI and spatial outputs are advisory candidates, not verified facts or regulatory decisions\n"
        "- Human review is required; automatic enforcement and official submissions are disabled"
    )
    st.markdown("**Not connected or production-ready**")
    st.markdown(
        "- No official NEMA, ELMIS or SWIMS integration\n"
        "- No live Google Earth Engine / Sentinel-2 acquisition in this workspace\n"
        "- No SMS/USSD/IVR, IoT sensor ingestion, or autonomous response\n"
        "- Production monitoring, independent backup/restore, and formal retention controls still require verification"
    )
    st.warning(
        "Before real-user deployment: configure secrets, test each role, establish backup/restore "
        "and retention controls, review data governance, and obtain the required institutional/supervisor approvals."
    )
