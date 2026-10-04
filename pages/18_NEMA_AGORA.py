"""NEMA-AGORA: authenticated pilot workspace.

Demo mode is session-only and safe for synthetic testing. Persistent mode is
explicitly opt-in and requires Streamlit OIDC plus a server-side role binding.
This remains an independent student-led prototype, not an official NEMA service.
"""
from __future__ import annotations

from datetime import date, datetime
import pandas as pd
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.core import CATEGORIES, SEVERITIES, STATUSES, make_observation, validate_observation
from nema_agora.governance import policy_from_secrets, validate_governance
from nema_agora.quality import assess_observation
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository
from nema_agora.workflow import apply_status_update

st.set_page_config(page_title="NEMA-AGORA Pilot", page_icon="🌿", layout="wide")


def _demo_init() -> None:
    st.session_state.setdefault("nema_agora_reports", [])
    st.session_state.setdefault("nema_agora_audit_events", [])


def _persistent_context() -> tuple[NemaAgoraService | None, object | None, str]:
    mode = mode_from_secrets(st.secrets)
    if mode != "persistent":
        return None, None, mode
    principal = principal_from_streamlit_user(st.user, st.secrets)
    if principal is None or not principal.is_authorised:
        return None, principal, mode
    database_path = database_path_from_secrets(st.secrets)
    if database_path is None:
        st.error("Persistent mode is enabled but nema_agora.database_path is not configured.")
        return None, principal, mode
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return NemaAgoraService(NemaAgoraRepository(database_path)), principal, mode


_demo_init()
service, principal, mode = _persistent_context()
governance_policy = policy_from_secrets(st.secrets)
governance_errors = validate_governance(governance_policy)
if governance_errors:
    st.error("NEMA-AGORA governance configuration is invalid; data intake is disabled.")
    for error in governance_errors:
        st.error(error)
    st.stop()

st.title("🌿 NEMA-AGORA")
st.caption("Environmental Governance, Monitoring & Response — pilot workspace")
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

tabs = st.tabs([
    "📝 Submit observation", "🔎 Review & track", "🧠 Evidence intelligence",
    "🗺️ Map", "📊 Pilot metrics", "ℹ️ About"
])
tab_report, tab_review, tab_intelligence, tab_map, tab_metrics, tab_about = tabs

with tab_report:
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

with tab_review:
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
            with st.form(f"review_{selected_id}"):
                new_status = st.selectbox("Status", STATUSES, index=STATUSES.index(selected["status"]))
                review_notes = st.text_area("Reviewer notes (avoid personal/sensitive data)", value=selected.get("review_notes", ""), max_chars=1000)
                reviewed = st.form_submit_button("Update status", type="primary")
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

with tab_intelligence:
    st.subheader("🧠 Evidence intelligence — human-in-the-loop")
    st.caption("Phase 8 foundation: deterministic, explainable and advisory. No autonomous regulatory or enforcement decisions are made.")
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
                analysis = service.analyze_observation(selected_ai, principal, peer_records=records)
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

with tab_map:
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

with tab_metrics:
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

with tab_about:
    st.subheader("Project purpose")
    st.write(
        "NEMA-AGORA is a proposed student-led pilot for organising environmental observations, "
        "review status, location information and evaluation data. It is designed to complement "
        "existing environmental-management systems, not replace them."
    )
    st.markdown("**Phase 8 — Evidence Intelligence & Human-in-the-Loop**")
    st.markdown(
        "- Neutral extractive summaries without invented facts\n"
        "- Explainable keyword-supported category suggestions\n"
        "- Review-priority advisories tied to existing pilot fields\n"
        "- Duplicate candidates as review signals only\n"
        "- Human verification remains mandatory\n"
        "- No autonomous regulatory, enforcement or environmental-truth decisions"
    )
    st.markdown("**Security and governance controls**")
    st.markdown(
        "- Streamlit OIDC identity → stable issuer + subject principal\n"
        "- Server-side role binding with deny-by-default access\n"
        "- Persistent repository operations require the authenticated principal\n"
        "- Submitters are isolated to records they own\n"
        "- Review, metrics, audit, export and intelligence are permission-gated\n"
        "- Personal-data intake, urgent incidents and unofficial integrations remain disabled"
    )
    st.markdown("**Still not implemented**")
    st.markdown(
        "- Official NEMA, ELMIS or SWIMS integration\n"
        "- Regulatory enforcement or verified incident classification\n"
        "- SMS/USSD/IVR, satellite analytics, IoT or predictive models\n"
        "- Production monitoring and independent backup/audit infrastructure"
    )
    st.warning(
        "Before real-user deployment: configure secrets, test each role, establish backup/restore "
        "and retention controls, review data governance, and obtain the required institutional/supervisor approvals."
    )
