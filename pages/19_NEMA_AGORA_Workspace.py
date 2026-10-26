"""NEMA-AGORA: authenticated pilot workspace.

Demo mode is session-only and safe for synthetic testing. Persistent mode is
explicitly opt-in and requires Streamlit OIDC plus a server-side role binding.
This remains an independent student-led prototype, not an official NEMA service.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
import pandas as pd
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.client import NemaApiError, get_case, get_review_packet, get_storage_readiness, list_cases
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
from nema_agora.satellite_evaluation import SatelliteEvaluationError, evaluate_change_candidates
from nema_agora.satellite_manifest import SatelliteManifestError, validate_dataset_manifest
from nema_agora.reference_review import ReferenceReviewError, validate_reference_review_package
from nema_agora.split_audit import SplitAuditError, audit_dataset_splits
from nema_agora.stac_discovery import StacDiscoveryError, discover_scenes
from nema_agora.raster_ingestion import RasterIngestionError, process_uploaded_geotiff
from nema_agora.paired_raster_ingestion import PairedRasterError, compare_uploaded_geotiff_pair
from nema_agora.spatial_workspace_bundle import build_spatial_evidence_bundle, validate_spatial_evidence_bundle

st.set_page_config(page_title="NEMA-AGORA Pilot", page_icon="🌿", layout="wide")


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
if mode == "persistent" and principal is not None and principal.is_authorised and service is None:
    st.stop()
governance_policy = policy_from_secrets(st.secrets)
governance_errors = validate_governance(governance_policy)
if governance_errors:
    st.error("NEMA-AGORA governance configuration is invalid; data intake is disabled.")
    for error in governance_errors:
        st.error(error)
    st.stop()

st.title("🌿 NEMA-AGORA")
st.caption("Environmental Governance, Monitoring & Response — pilot workspace")
st.markdown(
    "Use the workspace menu in the sidebar to move between tasks. Capture an observation, "
    "track human review, inspect advisory evidence, and review controlled reports."
)
quick = st.columns(4)
quick[0].markdown("**1 · Capture**")
quick[0].caption("Submit a structured observation.")
quick[1].markdown("**2 · Review**")
quick[1].caption("Check quality and record human decisions.")
quick[2].markdown("**3 · Understand**")
quick[2].caption("Inspect evidence and advisory analysis.")
quick[3].markdown("**4 · Report**")
quick[3].caption("Review metrics and controlled exports.")
st.info(
    "Independent student-led prototype. This is not an official NEMA service, "
    "does not submit reports to NEMA, and is not connected to ELMIS or SWIMS. "
    "Do not enter personal, confidential, or urgent incident information."
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
    st.subheader("Navigate workspace")
    active_section = st.radio(
        "Choose a work area",
        [
            "Submit observation",
            "Persisted cases & audit",
            "Case management",
            "Intelligence workspace",
            "Maps & metrics",
            "Governance & help",
        ],
        index=0,
        key="nema_agora_navigation",
        label_visibility="collapsed",
        help="Choose one work area. Related tools are grouped together to keep navigation short.",
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
        ["Map", "Pilot metrics", "Spatial evidence"],
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

if active_section == "Persisted cases & audit":
    st.subheader("Persisted cases & audit")
    st.caption("Read-only view of cases held by the Render-hosted case API. This panel does not create, edit, close, or enforce cases.")
    st.warning("Access requires an authenticated, server-provisioned NEMA-AGORA account. The API credential is server-side and is never displayed.")
    if not persistent or principal is None or not principal.is_authorised:
        st.info("Persisted case access is disabled until authenticated persistent mode and a server-provisioned role are active.")
    elif principal.role not in {"reviewer", "coordinator", "admin"}:
        st.warning("Cross-case records are restricted to reviewers, coordinators, and administrators. Submitter ownership filtering is not yet available.")
    else:
        with st.sidebar:
            st.subheader("Case API connection")
            if st.button("Refresh persisted cases", key="nema_refresh_persisted_cases", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
            st.caption("Connection credentials are read from server environment variables and are never shown.")

        @st.cache_data(ttl=30, show_spinner=False)
        def _nema_case_api_readiness(actor_id: str, actor_role: str):
            return get_storage_readiness(actor_id, actor_role)

        @st.cache_data(ttl=30, show_spinner=False)
        def _nema_case_api_list(actor_id: str, actor_role: str, limit: int):
            return list_cases(actor_id, actor_role, limit=limit)

        try:
            readiness = _nema_case_api_readiness(principal.subject_key, principal.role)
            status_value = str(readiness.get("status", "unknown")).lower()
            backend = readiness.get("storage_backend", "unknown")
            ready = status_value in {"configured", "ready"}
            metrics = st.columns(4)
            metrics[0].metric("Storage status", "Connected" if ready else status_value.replace("_", " ").title())
            metrics[1].metric("Backend", str(backend))
            metrics[2].metric("Production writes", "Enabled" if readiness.get("production_writes_enabled") else "Disabled")
            metrics[3].metric("Durability verified", "Yes" if readiness.get("storage_durability_verified") else "Not yet")
            if not readiness.get("production_writes_enabled"):
                st.info("Read-only safety mode is active. Storage connectivity does not certify production write readiness or backup/restore.")
        except NemaApiError:
            st.error("The persisted case API is not ready. Check the server-side API key and storage configuration, then retry.")
            st.stop()

        case_left, case_right = st.columns([1.1, 1])
        with case_left:
            st.markdown("#### Persisted cases")
            case_limit = st.selectbox("Maximum cases to load", [25, 50, 100, 250, 500, 1000], index=2, key="nema_persisted_case_limit")
            try:
                case_result = _nema_case_api_list(principal.subject_key, principal.role, case_limit)
                case_items = case_result.get("items", [])
                st.metric("Cases returned", int(case_result.get("count", len(case_items))))
                if not case_items:
                    st.info("No persisted cases were returned. Empty storage is valid until a governed, audited write workflow is enabled.")
                else:
                    case_options = []
                    case_ids = {}
                    for case_index, case_item in enumerate(case_items):
                        case_record = case_item.get("record", {})
                        case_id = str(case_record.get("case_id") or case_record.get("id") or f"record-{case_index + 1}")
                        case_label = str(case_record.get("title") or case_record.get("name") or case_id)
                        display_label = f"{case_label} · {case_id}"
                        case_options.append(display_label)
                        case_ids[display_label] = case_id
                    selected_label = st.selectbox("Select a case", case_options, key="nema_persisted_case_choice")
                    if st.button("Load case details", key="nema_load_persisted_case", type="primary"):
                        st.session_state["nema_selected_case_id"] = case_ids[selected_label]
            except NemaApiError:
                st.error("Cases could not be loaded. Check API health and access, then retry.")
                st.stop()

        with case_right:
            st.markdown("#### Case details and audit")
            selected_case_id = st.session_state.get("nema_selected_case_id")
            if not selected_case_id:
                st.caption("Select a case and choose Load case details to inspect its record and audit history.")
            else:
                try:
                    detail = get_case(selected_case_id, principal.subject_key, principal.role)
                    st.caption(f"Case ID: {selected_case_id} · Version: {detail.get('version', 'unknown')}")
                    st.json(detail.get("record", {}), expanded=True)
                    with st.expander("Audit history", expanded=False):
                        st.json(detail.get("audit", []), expanded=True)
                    if st.button("Generate review packet (read-only preview)", key="nema_generate_review_packet"):
                        try:
                            st.session_state["nema_review_packet"] = {
                                "case_id": selected_case_id,
                                "packet": get_review_packet(selected_case_id, principal.subject_key, principal.role),
                            }
                        except NemaApiError:
                            st.error("The review packet could not be prepared. Check API health and access, then retry.")
                    saved_packet = st.session_state.get("nema_review_packet", {})
                    if saved_packet.get("case_id") == selected_case_id:
                        st.markdown("#### Deterministic review packet")
                        st.caption("Preview only; this does not create a workflow job or change case data. Human review remains required.")
                        st.json(saved_packet.get("packet", {}), expanded=True)
                except NemaApiError:
                    st.error("Case details could not be loaded. Refresh the list and retry.")
        st.divider()
        st.caption("Governance: each request carries a server-signed OIDC subject and role. Cross-case reads are restricted to reviewer, coordinator, and admin roles; submitter-owned case filtering is not yet implemented. Do not use this view for enforcement or official compliance decisions.")

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
            evidence_reference = st.text_input("Evidence reference (optional)", placeholder="Non-sensitive file name or URL", max_chars=300)
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
            st.info("No records available.")
        else:
            selected_id = st.selectbox("Select record", options=[r["case_id"] for r in reversed(records)])
            selected = next(r for r in records if r["case_id"] == selected_id)
            st.markdown(f"**{selected['category']}** · {selected['severity']} · {selected['district_or_site']}")
            st.write(selected["description"])
            st.caption(f"Observed: {selected['observation_date']} · Created: {selected['created_at']}")
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
                    st.error(str(exc))
                else:
                    st.success("Record updated.")
                    st.rerun()
            if can_audit:
                events = visible_audit(selected_id)
                if events:
                    st.markdown("**Audit history**")
                    st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
            st.divider()
            st.dataframe(
                pd.DataFrame(records)[["case_id", "observation_date", "category", "severity", "district_or_site", "status"]],
                use_container_width=True, hide_index=True
            )
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
        st.warning("Prototype activity metrics are not verified environmental outcomes or official response statistics.")

    st.divider()
    st.subheader("Pilot results & indicator register")
    st.caption(
        "Measurement contract for the four proposed pilot results. Targets are not achievements; "
        "indicators remain not started until evidence is collected and checked."
    )
    registry_path = __import__("pathlib").Path(__file__).resolve().parents[1] / "nema_agora" / "indicator_registry.json"
    try:
        with registry_path.open("r", encoding="utf-8") as registry_file:
            indicator_registry = json.load(registry_file)
        indicators = indicator_registry["indicators"]
        allowed_statuses = set(indicator_registry["status_values"])
        if not all(item.get("status") in allowed_statuses for item in indicators):
            raise ValueError("Indicator registry contains an unsupported status.")
        status_counts = {status: sum(1 for item in indicators if item["status"] == status) for status in allowed_statuses}
        status_cols = st.columns(4)
        status_cols[0].metric("Indicators defined", len(indicators))
        status_cols[1].metric("Measured", status_counts.get("measured", 0))
        status_cols[2].metric("Verified", status_counts.get("verified", 0))
        status_cols[3].metric("Blocked", status_counts.get("blocked", 0))
        display_rows = []
        for item in indicators:
            target = item.get("target")
            if target is None:
                target_label = "Baseline to establish"
            elif item.get("target_type") == "less_than_p95":
                target_label = f"p95 < {target} {item.get('unit', '')}"
            elif item.get("target_type") == "stretch_target_on_declared_evaluation_set":
                target_label = f"{target}% on declared evaluation set"
            else:
                target_label = f"{target} {item.get('unit', '')}"
            display_rows.append({
                "Result": item.get("result_id", "—"),
                "Indicator": item.get("name", item.get("id", "Unnamed")),
                "Target": target_label,
                "Status": item.get("status", "not_started"),
                "Evidence required": "; ".join(item.get("required_evidence", [])),
            })
        st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
        with st.expander("Indicator definitions and verification rules", expanded=False):
            for item in indicators:
                st.markdown(f"**{item.get('id', 'Indicator')} — {item.get('name', 'Unnamed')}**")
                st.write(item.get("calculation", "Calculation method not yet defined."))
                companions = item.get("quality_companions", [])
                if companions:
                    st.caption("Quality checks: " + ", ".join(companions))
                if item.get("caveat"):
                    st.warning(item["caveat"])
        st.info(
            "Evidence gate: a target must not be marked measured or verified without a defined reporting period, "
            "calculation, denominator where applicable, source records, and a reviewable evidence reference."
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        st.error("The indicator register could not be loaded or failed validation. No indicator status is being reported.");


if active_section == "Maps & metrics" and map_tool == "Pilot metrics":
    st.divider()
    st.subheader("Offline satellite evaluation (evidence-gated)")
    st.caption(
        "Evaluate a prepared reference dataset or inspect a clearly labelled synthetic example. "
        "This does not fetch imagery, run a satellite model, or measure live pilot performance."
    )
    st.info(
        "CSV columns required: unit_id, area_ha, detected, reference_change, "
        "independently_verified, usable. Boolean columns must contain true/false values. "
        "Use independently reviewed reference labels; never upload confidential or personal data."
    )
    template_columns = ["unit_id", "area_ha", "detected", "reference_change", "independently_verified", "usable"]
    st.download_button(
        "Download CSV template",
        data=",".join(template_columns) + "\n",
        file_name="nema_satellite_evaluation_template.csv",
        mime="text/csv",
        key="nema_satellite_eval_template",
    )
    evaluation_file = st.file_uploader(
        "Upload evaluation fixture CSV",
        type=["csv"],
        key="nema_satellite_eval_csv",
        help="Expected columns are listed above. The file is processed for this Streamlit session only.",
    )
    eval_left, eval_right = st.columns([1, 2])
    with eval_left:
        area_threshold = st.number_input(
            "Minimum area threshold (ha)",
            min_value=0.0,
            value=0.1,
            step=0.05,
            format="%.2f",
            key="nema_satellite_eval_area_threshold",
        )
        run_synthetic = st.button(
            "Run synthetic example",
            key="nema_run_synthetic_satellite_eval",
            use_container_width=True,
        )
        run_uploaded = st.button(
            "Evaluate uploaded CSV",
            key="nema_run_uploaded_satellite_eval",
            type="primary",
            use_container_width=True,
            disabled=evaluation_file is None,
        )
    if run_synthetic or run_uploaded:
        try:
            if run_synthetic:
                fixture = [
                    {"unit_id": "SYN-TP", "area_ha": 0.22, "detected": True, "reference_change": True, "independently_verified": True, "usable": True},
                    {"unit_id": "SYN-FP", "area_ha": 0.18, "detected": True, "reference_change": False, "independently_verified": True, "usable": True},
                    {"unit_id": "SYN-FN", "area_ha": 0.25, "detected": False, "reference_change": True, "independently_verified": True, "usable": True},
                    {"unit_id": "SYN-TN", "area_ha": 0.30, "detected": False, "reference_change": False, "independently_verified": True, "usable": True},
                    {"unit_id": "SYN-EXCLUDED", "area_ha": 0.10, "detected": True, "reference_change": True, "independently_verified": True, "usable": True},
                ]
                source_bytes = json.dumps(fixture, sort_keys=True, separators=(",", ":")).encode("utf-8")
                source_name = "built-in-synthetic-fixture"
                result_label = "SYNTHETIC EXAMPLE — NOT REAL SATELLITE RESULTS"
            else:
                required_columns = {
                    "unit_id", "area_ha", "detected", "reference_change",
                    "independently_verified", "usable",
                }
                source_bytes = evaluation_file.getvalue()
                source_name = str(evaluation_file.name)
                frame = pd.read_csv(io.BytesIO(source_bytes))
                missing = sorted(required_columns - set(frame.columns))
                if missing:
                    raise SatelliteEvaluationError("Missing required CSV columns: " + ", ".join(missing))
                boolean_columns = ["detected", "reference_change", "independently_verified", "usable"]
                fixture = []
                for row_index, row in frame.iterrows():
                    parsed = {}
                    for column in boolean_columns:
                        value = row[column]
                        normalized = str(value).strip().lower()
                        if normalized in {"true", "false"}:
                            parsed[column] = normalized == "true"
                        else:
                            raise SatelliteEvaluationError(
                                f"Row {row_index + 2}: {column} must be true or false."
                            )
                    fixture.append({
                        "unit_id": row["unit_id"],
                        "area_ha": row["area_ha"],
                        **parsed,
                    })
                result_label = "UPLOADED FIXTURE — RESULTS APPLY ONLY TO THIS DATASET"
            result = evaluate_change_candidates(fixture, min_area_ha=area_threshold)
        except (SatelliteEvaluationError, ValueError, TypeError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            st.error("Evaluation could not be completed. Check the CSV format and required values.")
            st.caption(str(exc))
        else:
            provenance = {
                "source_name": source_name,
                "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "input_record_count": len(fixture),
                "area_threshold_ha": float(area_threshold),
                "evaluation_version": result["evaluation_version"],
                "interpretation": result["interpretation"],
            }
            report_digest_input = json.dumps(
                {"provenance": provenance, "evaluation": result},
                sort_keys=True, separators=(",", ":"), allow_nan=False,
            ).encode("utf-8")
            provenance["report_sha256"] = hashlib.sha256(report_digest_input).hexdigest()
            st.session_state["nema_satellite_evaluation_result"] = {
                "label": result_label,
                "result": result,
                "provenance": provenance,
            }
    saved_evaluation = st.session_state.get("nema_satellite_evaluation_result")
    if saved_evaluation:
        result = saved_evaluation["result"]
        st.warning(saved_evaluation["label"])
        counts = result["counts"]
        metrics = result["metrics"]
        stat_cols = st.columns(4)
        stat_cols[0].metric("Eligible units", counts["eligible_units"])
        stat_cols[1].metric("Precision", "N/A" if metrics["precision"] is None else f'{metrics["precision"]:.1%}')
        stat_cols[2].metric("Recall", "N/A" if metrics["recall"] is None else f'{metrics["recall"]:.1%}')
        stat_cols[3].metric("False-positive rate", "N/A" if metrics["false_positive_rate"] is None else f'{metrics["false_positive_rate"]:.1%}')
        st.write(f"**Evaluation state:** {result['state']} · **Version:** {result['evaluation_version']}")
        provenance = saved_evaluation["provenance"]
        with st.expander("Evaluation provenance & reproducibility", expanded=True):
            st.write(f"**Source:** {provenance['source_name']}")
            st.write(f"**Source SHA-256:** {provenance['source_sha256']}")
            st.write(f"**Report SHA-256:** {provenance['report_sha256']}")
            st.write(f"**Evaluated at (UTC):** {provenance['created_at_utc']}")
            st.write(f"**Input records:** {provenance['input_record_count']}")
            st.caption("The source digest identifies the exact uploaded bytes (or canonical synthetic fixture); the report digest detects changes to the evaluated output. Neither proves reference-label accuracy or dataset representativeness.")
        st.dataframe(
            pd.DataFrame([
                {"Measure": "True positives", "Count": counts["true_positive"]},
                {"Measure": "False positives", "Count": counts["false_positive"]},
                {"Measure": "False negatives", "Count": counts["false_negative"]},
                {"Measure": "True negatives", "Count": counts["true_negative"]},
                {"Measure": "Excluded units", "Count": counts["excluded_units"]},
            ]),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("F1 score: " + ("N/A (undefined denominator)" if metrics["f1_score"] is None else f'{metrics["f1_score"]:.1%}'))
        if any(result["exclusions"].values()):
            st.write("**Exclusions**")
            st.json(result["exclusions"], expanded=False)
        st.write("**Limitations**")
        for limitation in result["limitations"]:
            st.caption("• " + limitation)
        st.download_button(
            "Download evaluation report (JSON)",
            data=json.dumps({"label": saved_evaluation["label"], "provenance": saved_evaluation["provenance"], "evaluation": result}, indent=2, allow_nan=False),
            file_name="nema_satellite_evaluation_report.json",
            mime="application/json",
            key="nema_download_satellite_eval_json",
        )


if active_section == "Maps & metrics" and map_tool == "Pilot metrics":
    st.divider()
    st.subheader("Satellite dataset manifest (provenance gate)")
    st.caption(
        "Validate metadata completeness before treating an evaluation as review-ready. "
        "This does not fetch or authenticate source imagery or independently verify reference labels."
    )
    manifest_template = {
        "dataset_id": "replace-with-dataset-id",
        "aoi_id": "replace-with-area-of-interest-id",
        "sensor": "Sentinel-2",
        "product_id": "replace-with-product-id",
        "processing_version": "record-processing-version",
        "crs": "record-CRS",
        "grid_id": "record-grid-version",
        "reference_set_id": "record-reference-set-id",
        "reference_set_version": "record-reference-set-version",
        "sampling_method": "describe-sampling",
        "label_review_method": "describe-independent-review",
        "candidate_policy_version": "record-policy-version",
        "split": "development",
        "acquisition_start": "2026-01-01",
        "acquisition_end": "2026-01-31",
        "cloud_filter_method": "describe-cloud-filter",
        "valid_pixel_method": "describe-valid-pixel-filter",
        "spatial_resolution_m": 10.0,
        "cloud_cover_pct": 20.0,
        "valid_pixel_fraction": 0.8,
        "source_sha256": "replace-with-64-character-source-sha256",
    }
    st.download_button(
        "Download manifest JSON template",
        data=json.dumps(manifest_template, indent=2),
        file_name="nema_satellite_dataset_manifest_template.json",
        mime="application/json",
        key="nema_satellite_manifest_template",
    )
    manifest_file = st.file_uploader(
        "Upload dataset manifest JSON",
        type=["json"],
        key="nema_satellite_manifest_json",
        help="Replace every placeholder with the actual dataset metadata before validation.",
    )
    if st.button("Validate dataset manifest", key="nema_validate_satellite_manifest"):
        if manifest_file is None:
            st.warning("Upload a manifest JSON file first.")
        else:
            try:
                parsed_manifest = json.loads(manifest_file.getvalue().decode("utf-8"))
                validation = validate_dataset_manifest(parsed_manifest)
                st.session_state["nema_satellite_manifest_validation"] = validation
            except (UnicodeDecodeError, json.JSONDecodeError, SatelliteManifestError) as exc:
                st.session_state.pop("nema_satellite_manifest_validation", None)
                st.error(f"Manifest rejected: {exc}")
    manifest_validation = st.session_state.get("nema_satellite_manifest_validation")
    if manifest_validation:
        st.warning("Metadata completeness is not independent verification. Review all warnings before using this manifest.")
        st.write(f"**State:** {manifest_validation['state']}")
        st.write(f"**Manifest SHA-256:** {manifest_validation['manifest_sha256']}")
        for warning in manifest_validation["warnings"]:
            st.caption("• " + warning)
        st.download_button(
            "Download validated manifest report",
            data=json.dumps(manifest_validation, indent=2, allow_nan=False),
            file_name="nema_satellite_manifest_validation_report.json",
            mime="application/json",
            key="nema_satellite_manifest_validation_report",
        )


if active_section == "Maps & metrics" and map_tool == "Pilot metrics":
    st.divider()
    st.subheader("Independent reference-label review gate")
    st.caption(
        "Validate declared review traceability before an evaluation package is considered review-ready. "
        "This does not authenticate reviewers, inspect evidence assets, or prove label accuracy."
    )
    st.info(
        "Each unit must have a stable ID, a boolean reference label, at least two distinct reviewers, "
        "a timezone-aware review timestamp, evidence references, and an explicit declaration that reviewers "
        "were blinded to candidate detections."
    )
    reference_review_template = {
        "reference_set_id": "uganda-wetland-reference",
        "reference_set_version": "v1",
        "split": "development",
        "units": [{
            "unit_id": "unit-001",
            "reference_change": True,
            "reviewer_ids": ["reviewer-a", "reviewer-b"],
            "reviewed_at": "2026-02-01T10:30:00Z",
            "evidence_refs": ["imagery:product-id", "field-note:record-id"],
            "reviewers_blinded_to_candidate": True
        }]
    }
    st.download_button(
        "Download reference-review JSON template",
        data=json.dumps(reference_review_template, indent=2),
        file_name="nema_reference_review_template.json",
        mime="application/json",
        key="nema_reference_review_template",
    )
    reference_review_file = st.file_uploader(
        "Upload reference-review package JSON",
        type=["json"],
        key="nema_reference_review_json",
    )
    if st.button(
        "Validate reference-review package",
        key="nema_validate_reference_review",
        disabled=reference_review_file is None,
    ):
        try:
            package = json.loads(reference_review_file.getvalue().decode("utf-8"))
            result = validate_reference_review_package(package)
            st.session_state["nema_reference_review_validation"] = result
        except (UnicodeDecodeError, json.JSONDecodeError, ReferenceReviewError) as exc:
            st.session_state.pop("nema_reference_review_validation", None)
            st.error(f"Reference-review package rejected: {exc}")
    reference_review_result = st.session_state.get("nema_reference_review_validation")
    if reference_review_result:
        st.warning(
            "Metadata-complete only. Reviewer identities, evidence references, blinding and holdout independence "
            "remain declarations requiring independent audit."
        )
        st.write(f"**State:** {reference_review_result['state']}")
        st.write(
            f"**Reference set:** {reference_review_result['reference_set_id']} "
            f"· **Version:** {reference_review_result['reference_set_version']} "
            f"· **Split:** {reference_review_result['split']}"
        )
        st.write(f"**Units reviewed:** {reference_review_result['reviewed_unit_count']}")
        st.write(f"**Package SHA-256:** {reference_review_result['package_sha256']}")
        for limitation in reference_review_result["limitations"]:
            st.caption("• " + limitation)
        st.download_button(
            "Download reference-review validation report",
            data=json.dumps(reference_review_result, indent=2, allow_nan=False),
            file_name="nema_reference_review_validation_report.json",
            mime="application/json",
            key="nema_reference_review_validation_report",
        )


if active_section == "Maps & metrics" and map_tool == "Pilot metrics":
    st.divider()
    st.subheader("Dataset split leakage audit")
    st.caption(
        "Compare declared unit IDs across development, validation and holdout manifests before calculating metrics. "
        "This catches exact-ID overlap only; it is not proof of complete spatial, temporal, or evidence independence."
    )
    split_template = {
        "manifests": [
            {"reference_set_id": "uganda-wetland-reference", "reference_set_version": "v1",
             "split": "development", "unit_ids": ["unit-001", "unit-002"]},
            {"reference_set_id": "uganda-wetland-reference", "reference_set_version": "v1",
             "split": "validation", "unit_ids": ["unit-003"]},
            {"reference_set_id": "uganda-wetland-reference", "reference_set_version": "v1",
             "split": "holdout", "unit_ids": ["unit-004"]}
        ]
    }
    st.download_button(
        "Download split-audit JSON template",
        data=json.dumps(split_template, indent=2),
        file_name="nema_dataset_split_audit_template.json",
        mime="application/json",
        key="nema_split_audit_template_download",
    )
    split_manifest_file = st.file_uploader(
        "Upload dataset split manifests JSON",
        type=["json"],
        key="nema_split_audit_json",
        help="Expected shape: an object with a non-empty 'manifests' array. Each entry requires reference_set_id, reference_set_version, split and unit_ids.",
    )
    if st.button(
        "Audit dataset split overlap",
        key="nema_audit_dataset_splits",
        disabled=split_manifest_file is None,
    ):
        try:
            split_payload = json.loads(split_manifest_file.getvalue().decode("utf-8"))
            if not isinstance(split_payload, dict) or "manifests" not in split_payload:
                raise SplitAuditError("upload must be an object containing a 'manifests' array.")
            split_report = audit_dataset_splits(split_payload["manifests"])
            st.session_state["nema_split_audit_report"] = split_report
        except (UnicodeDecodeError, json.JSONDecodeError, SplitAuditError) as exc:
            st.session_state.pop("nema_split_audit_report", None)
            st.error(f"Dataset split audit rejected: {exc}")
    split_report = st.session_state.get("nema_split_audit_report")
    if split_report:
        if split_report["decision"] == "NO_DECLARED_UNIT_ID_OVERLAP":
            st.success("No exact unit-ID overlap was found in the supplied declarations.")
        else:
            st.error("Declared split overlap found. Block evaluation until the split design is corrected.")
        st.write(f"**State:** {split_report['state']}")
        st.write(f"**Manifest SHA-256:** {split_report['manifest_sha256']}")
        st.dataframe(
            [
                {"Reference set": set_id, "Split": split, "Declared units": count}
                for set_id, counts in split_report["split_unit_counts"].items()
                for split, count in counts.items()
            ],
            use_container_width=True,
            hide_index=True,
        )
        if split_report["overlaps"]:
            st.subheader("Overlaps requiring resolution")
            st.dataframe(split_report["overlaps"], use_container_width=True, hide_index=True)
        for limitation in split_report["limitations"]:
            st.caption("• " + limitation)
        st.download_button(
            "Download dataset split audit report",
            data=json.dumps(split_report, indent=2, allow_nan=False),
            file_name="nema_dataset_split_audit_report.json",
            mime="application/json",
            key="nema_split_audit_report_download",
        )


if active_section == "Maps & metrics" and map_tool == "Pilot metrics":
    st.divider()
    st.subheader("Live catalogue discovery (metadata only)")
    st.caption(
        "Optional network request to the fixed public Earth Search STAC catalogue for Sentinel-2 L2A scene metadata. "
        "This does not download imagery, calculate indices, or establish environmental change."
    )
    with st.expander("Search satellite scene catalogue", expanded=False):
        st.warning("Use a WGS84 bounding box (longitude/latitude). Scene cloud cover is not AOI-specific valid-pixel quality.")
        col_w, col_s, col_e, col_n = st.columns(4)
        with col_w:
            bbox_west = st.number_input("West longitude", min_value=-180.0, max_value=180.0, value=32.0, step=0.1, key="nema_stac_west")
        with col_s:
            bbox_south = st.number_input("South latitude", min_value=-90.0, max_value=90.0, value=0.5, step=0.1, key="nema_stac_south")
        with col_e:
            bbox_east = st.number_input("East longitude", min_value=-180.0, max_value=180.0, value=33.0, step=0.1, key="nema_stac_east")
        with col_n:
            bbox_north = st.number_input("North latitude", min_value=-90.0, max_value=90.0, value=1.5, step=0.1, key="nema_stac_north")
        date_col_a, date_col_b, cloud_col, limit_col = st.columns(4)
        with date_col_a:
            acquisition_start = st.date_input("Acquisition start", value=datetime.now(timezone.utc).date() - timedelta(days=30), key="nema_stac_start")
        with date_col_b:
            acquisition_end = st.date_input("Acquisition end", value=datetime.now(timezone.utc).date(), key="nema_stac_end")
        with cloud_col:
            max_cloud = st.number_input("Max scene cloud cover (%)", min_value=0.0, max_value=100.0, value=30.0, step=5.0, key="nema_stac_cloud")
        with limit_col:
            scene_limit = st.number_input("Maximum scenes", min_value=1, max_value=100, value=20, step=1, key="nema_stac_limit")
        aoi_id = st.text_input("Stable AOI identifier", value="UG-PILOT-AOI-01", key="nema_stac_aoi")
        if st.button("Search public catalogue", key="nema_stac_search"):
            try:
                with st.spinner("Searching scene metadata; no imagery is downloaded…"):
                    report = discover_scenes(
                        aoi_id=aoi_id,
                        bbox=[bbox_west, bbox_south, bbox_east, bbox_north],
                        start_date=acquisition_start.isoformat(),
                        end_date=acquisition_end.isoformat(),
                        max_cloud_cover_pct=float(max_cloud),
                        limit=int(scene_limit),
                    )
                st.session_state["nema_stac_discovery_report"] = report
            except StacDiscoveryError as exc:
                st.session_state.pop("nema_stac_discovery_report", None)
                st.error(f"Catalogue search blocked or failed: {exc}")
    stac_report = st.session_state.get("nema_stac_discovery_report")
    if stac_report:
        st.write(f"**Catalogue result:** {stac_report['state']}")
        st.write(f"**Scenes accepted for metadata review:** {len(stac_report['scenes'])}")
        st.write(f"**Rejected metadata records:** {len(stac_report['rejected'])}")
        if stac_report["scenes"]:
            st.dataframe([
                {"Item ID": scene["item_id"], "Acquired": scene["acquired_at"],
                 "Cloud cover (%)": scene["cloud_cover_pct"], "Platform": scene["platform"],
                 "Available asset references": len(scene["assets"])}
                for scene in stac_report["scenes"]
            ], use_container_width=True, hide_index=True)
        if stac_report["rejected"]:
            with st.expander("Rejected catalogue records"):
                st.json(stac_report["rejected"])
        for limitation in stac_report["limitations"]:
            st.caption("• " + limitation)
        st.download_button(
            "Download STAC discovery report (JSON)",
            data=json.dumps(stac_report, indent=2, allow_nan=False),
            file_name="nema_stac_scene_discovery_report.json",
            mime="application/json",
            key="nema_stac_discovery_report_download",
        )


if active_section == "Maps & metrics" and map_tool == "Pilot metrics":
    st.divider()
    st.subheader("Process supplied Sentinel-2 GeoTIFF")
    st.caption(
        "Runs local pixel calculations only after validating a user-supplied multi-band GeoTIFF. "
        "No remote imagery is fetched. This screening output requires expert review."
    )
    st.warning(
        "Required bands must be named in the file metadata as B03, B04, B08 and SCL. "
        "All reflectance bands must use compatible scaling. If using an AOI GeoJSON, it must already "
        "use the raster's CRS; this tool does not reproject or resample."
    )
    raster_upload = st.file_uploader(
        "Multi-band GeoTIFF (max 100 MiB; named B03, B04, B08, SCL)",
        type=["tif", "tiff"],
        key="nema_pixel_geotiff_upload",
    )
    aoi_upload = st.file_uploader(
        "Optional AOI GeoJSON (Polygon or MultiPolygon; max 5 MiB)",
        type=["json", "geojson"],
        key="nema_pixel_aoi_upload",
    )
    aoi_crs_confirmed = False
    if aoi_upload is not None:
        aoi_crs_confirmed = st.checkbox(
            "I have verified that the AOI GeoJSON coordinates already use the exact CRS shown in the raster metadata.",
            key="nema_pixel_aoi_crs_confirmation",
        )
    if st.button("Validate raster and calculate indices", key="nema_pixel_process_button", type="primary"):
        if raster_upload is None:
            st.error("Upload a GeoTIFF before processing.")
            st.session_state.pop("nema_pixel_processing_report", None)
        elif aoi_upload is not None and not aoi_crs_confirmed:
            st.error("AOI processing is blocked until the same-CRS confirmation is checked.")
            st.session_state.pop("nema_pixel_processing_report", None)
        else:
            try:
                with st.spinner("Validating raster metadata and calculating masked indices…"):
                    report = process_uploaded_geotiff(
                        raster_upload.getvalue(),
                        aoi_geojson_bytes=aoi_upload.getvalue() if aoi_upload is not None else None,
                        aoi_crs_confirmed_same_as_raster=aoi_crs_confirmed,
                    )
                st.session_state["nema_pixel_processing_report"] = report
            except RasterIngestionError as exc:
                st.session_state.pop("nema_pixel_processing_report", None)
                st.error(f"Raster processing blocked: {exc}")
    pixel_report = st.session_state.get("nema_pixel_processing_report")
    if pixel_report:
        st.warning("Screening result only — not a verified environmental finding, wetland boundary, or enforcement decision.")
        st.write(f"**Processing state:** {pixel_report['state']}")
        st.write(f"**Source SHA-256:** {pixel_report['source']['source_sha256']}")
        st.write(f"**CRS:** {pixel_report['source']['crs']}")
        st.write(f"**Grid:** {pixel_report['source']['width_pixels']} × {pixel_report['source']['height_pixels']} pixels")
        st.write(f"**Valid AOI pixels:** {pixel_report['quality']['aoi_pixel_count']}")
        st.dataframe([
            {
                "Index": name,
                "Valid pixels": stats["valid_pixel_count"],
                "Valid fraction": round(stats["valid_pixel_fraction_within_aoi"], 4),
                "Median": stats["median"],
                "Mean": stats["mean"],
                "P05": stats["p05"],
                "P95": stats["p95"],
            }
            for name, stats in pixel_report["indices"].items()
        ], use_container_width=True, hide_index=True)
        with st.expander("Source metadata, quality checks and limitations"):
            st.json({
                "source": pixel_report["source"],
                "quality": pixel_report["quality"],
                "limitations": pixel_report["limitations"],
                "index_report_sha256": pixel_report["report_sha256"],
                "processing_report_sha256": pixel_report["processing_report_sha256"],
            })
        st.download_button(
            "Download pixel screening report (JSON)",
            data=json.dumps(pixel_report, sort_keys=True, indent=2, allow_nan=False),
            file_name="nema_sentinel2_pixel_screening_report.json",
            mime="application/json",
            key="nema_pixel_report_download",
        )


if active_section == "Maps & metrics" and map_tool == "Pilot metrics":
    st.divider()
    st.subheader("Compare two supplied Sentinel-2 dates")
    st.caption(
        "Paired local GeoTIFF screening with strict grid compatibility checks and a shared AOI/valid-pixel mask. "
        "This does not fetch imagery or make an environmental finding."
    )
    st.warning(
        "Both files must contain B03, B04, B08 and SCL bands with explicit descriptions. "
        "Reflectance scale and processing baseline must be verified from the original product metadata; "
        "the labels below are operator declarations, not independently authenticated facts."
    )
    st.info(
        "Scientific interpretation gate: compare like seasons where possible. Rainfall, seasonal vegetation, "
        "water-level changes, illumination, haze, cloud edges and shadows can create index differences. "
        "SCL filtering reduces some contamination but does not guarantee cloud-free pixels. Review source imagery "
        "and contextual evidence before treating a signal as persistent change."
    )
    earlier_upload = st.file_uploader(
        "Earlier-date multi-band GeoTIFF (max 100 MiB)",
        type=["tif", "tiff"], key="nema_pair_earlier_upload",
    )
    later_upload = st.file_uploader(
        "Later-date multi-band GeoTIFF (max 100 MiB)",
        type=["tif", "tiff"], key="nema_pair_later_upload",
    )
    pair_aoi_upload = st.file_uploader(
        "Optional shared AOI GeoJSON (max 5 MiB)",
        type=["json", "geojson"], key="nema_pair_aoi_upload",
    )
    col_earlier, col_later = st.columns(2)
    with col_earlier:
        earlier_acquired_at = st.text_input(
            "Earlier acquisition time (ISO-8601 with timezone)",
            placeholder="2026-01-15T10:20:00Z", key="nema_pair_earlier_date",
        )
    with col_later:
        later_acquired_at = st.text_input(
            "Later acquisition time (ISO-8601 with timezone)",
            placeholder="2026-02-14T10:20:00Z", key="nema_pair_later_date",
        )
    st.caption("Enter metadata identifiers separately for each acquisition. The workflow blocks mismatches; entries remain operator declarations and must be checked against original product metadata.")
    scale_a_col, scale_b_col = st.columns(2)
    with scale_a_col:
        earlier_reflectance_scale_id = st.text_input(
            "Earlier date — reflectance scale/product identifier",
            placeholder="e.g. L2A reflectance DN scaled by 10000",
            key="nema_pair_earlier_scale_id",
        )
    with scale_b_col:
        later_reflectance_scale_id = st.text_input(
            "Later date — reflectance scale/product identifier",
            placeholder="Same identifier only if verified",
            key="nema_pair_later_scale_id",
        )
    baseline_a_col, baseline_b_col = st.columns(2)
    with baseline_a_col:
        earlier_processing_baseline = st.text_input(
            "Earlier date — processing baseline",
            placeholder="e.g. 04.00", key="nema_pair_earlier_baseline",
        )
    with baseline_b_col:
        later_processing_baseline = st.text_input(
            "Later date — processing baseline",
            placeholder="Same baseline only if verified", key="nema_pair_later_baseline",
        )
    pair_aoi_crs_confirmed = False
    if pair_aoi_upload is not None:
        pair_aoi_crs_confirmed = st.checkbox(
            "I verified that this AOI GeoJSON uses the exact CRS of both rasters.",
            key="nema_pair_aoi_crs_confirmation",
        )
    col_ndvi, col_ndwi, col_coverage = st.columns(3)
    with col_ndvi:
        pair_ndvi_threshold = st.number_input(
            "NDVI absolute-change threshold", min_value=0.001, max_value=2.0,
            value=0.15, step=0.01, key="nema_pair_ndvi_threshold",
        )
    with col_ndwi:
        pair_ndwi_threshold = st.number_input(
            "NDWI absolute-change threshold", min_value=0.001, max_value=2.0,
            value=0.15, step=0.01, key="nema_pair_ndwi_threshold",
        )
    with col_coverage:
        pair_minimum_coverage = st.number_input(
            "Minimum shared valid fraction", min_value=0.01, max_value=1.0,
            value=0.70, step=0.05, key="nema_pair_minimum_coverage",
        )
    if st.button("Validate both dates and compare indices", key="nema_pair_compare_button", type="primary"):
        if earlier_upload is None or later_upload is None:
            st.error("Upload both earlier and later GeoTIFF files before comparing.")
            st.session_state.pop("nema_pair_change_report", None)
        elif not earlier_acquired_at.strip() or not later_acquired_at.strip():
            st.error("Both acquisition timestamps are required.")
            st.session_state.pop("nema_pair_change_report", None)
        elif not all(value.strip() for value in (earlier_reflectance_scale_id, later_reflectance_scale_id, earlier_processing_baseline, later_processing_baseline)):
            st.error("Supply the reflectance scale/product identifier and processing baseline for both dates.")
            st.session_state.pop("nema_pair_change_report", None)
        elif pair_aoi_upload is not None and not pair_aoi_crs_confirmed:
            st.error("AOI comparison is blocked until same-CRS confirmation is checked.")
            st.session_state.pop("nema_pair_change_report", None)
        else:
            try:
                with st.spinner("Validating both raster grids, applying shared masks and comparing indices…"):
                    pair_report = compare_uploaded_geotiff_pair(
                        earlier_upload.getvalue(),
                        later_upload.getvalue(),
                        earlier_acquired_at=earlier_acquired_at.strip(),
                        later_acquired_at=later_acquired_at.strip(),
                        earlier_reflectance_scale_id=earlier_reflectance_scale_id.strip(),
                        later_reflectance_scale_id=later_reflectance_scale_id.strip(),
                        earlier_processing_baseline=earlier_processing_baseline.strip(),
                        later_processing_baseline=later_processing_baseline.strip(),
                        aoi_geojson_bytes=pair_aoi_upload.getvalue() if pair_aoi_upload is not None else None,
                        aoi_crs_confirmed_same_as_rasters=pair_aoi_crs_confirmed,
                        ndvi_change_threshold=float(pair_ndvi_threshold),
                        ndwi_change_threshold=float(pair_ndwi_threshold),
                        minimum_valid_fraction=float(pair_minimum_coverage),
                    )
                st.session_state["nema_pair_change_report"] = pair_report
            except PairedRasterError as exc:
                st.session_state.pop("nema_pair_change_report", None)
                st.error(f"Two-date comparison blocked: {exc}")
    pair_report = st.session_state.get("nema_pair_change_report")
    if pair_report:
        st.warning(
            "Screening only. Threshold-exceedance counts are not proof of environmental change, "
            "wetland loss, causation, a legal violation or enforcement evidence."
        )
        st.write(f"**State:** {pair_report['state']}")
        st.write(f"**Shared valid pixels:** {pair_report['compatibility']['shared_valid_pixel_count']:,} / "
                 f"{pair_report['compatibility']['total_comparison_domain_pixels']:,}")
        st.write(f"**Shared valid fraction:** {pair_report['compatibility']['shared_valid_pixel_fraction']:.1%}")
        st.dataframe([
            {
                "Change measure": name,
                "Median delta": stats["median_delta"],
                "Mean delta": stats["mean_delta"],
                "P05 delta": stats["p05_delta"],
                "P95 delta": stats["p95_delta"],
                "Pixels above +threshold": stats["pixels_above_positive_threshold"],
                "Pixels below -threshold": stats["pixels_below_negative_threshold"],
                "Threshold": stats["absolute_change_threshold"],
            }
            for name, stats in pair_report["indices"].items()
        ], use_container_width=True, hide_index=True)
        with st.expander("Paired source provenance, compatibility and limitations"):
            st.json(pair_report)
        st.download_button(
            "Download two-date comparison report (JSON)",
            data=json.dumps(pair_report, sort_keys=True, indent=2, allow_nan=False),
            file_name="nema_sentinel2_two_date_comparison.json",
            mime="application/json",
            key="nema_pair_change_report_download",
        )


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
