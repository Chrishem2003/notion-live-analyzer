"""NEMA-AGORA: student-led environmental reporting pilot.

This first MVP is intentionally session-based: records are not persisted to a
database and must not be used for operational enforcement or sensitive reports.
"""
from __future__ import annotations

from datetime import date, datetime
import csv
import io
import pandas as pd
import streamlit as st

from nema_agora.core import CATEGORIES, SEVERITIES, STATUSES, make_observation, validate_observation

st.set_page_config(page_title="NEMA-AGORA Pilot", page_icon="🌿", layout="wide")

def _init_state() -> None:
    if "nema_agora_reports" not in st.session_state:
        st.session_state.nema_agora_reports = []


def _csv_bytes(records: list[dict]) -> bytes:
    """Return UTF-8 CSV for the currently visible pilot records."""
    fields = [
        "case_id", "created_at", "observation_date", "category", "severity",
        "district_or_site", "description", "latitude", "longitude", "status",
        "review_notes", "evidence_reference",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue().encode("utf-8-sig")


_init_state()
st.title("🌿 NEMA-AGORA")
st.caption("Environmental Governance, Monitoring & Response — pilot workspace")
st.info(
    "Independent student-led prototype. This is not an official NEMA service, "
    "does not submit reports to NEMA, and is not connected to ELMIS or SWIMS. "
    "Records are held in the current Streamlit session only and may disappear "
    "when the session restarts. Do not enter personal, confidential, or urgent "
    "incident information."
)

with st.sidebar:
    st.header("Pilot scope")
    st.write("**Current workflow:** report → review → status tracking → map/export.")
    st.write("**Data mode:** session-only demonstration data.")
    st.write("**Next milestone:** permissioned user testing and persistent storage "
             "only after privacy/security design.")
    st.divider()
    st.markdown("[Project source on GitHub](https://github.com/Chrishem2003/notion-live-analyzer)")
    st.markdown("[Applicant LinkedIn](https://www.linkedin.com/in/chris-shem-435166314)")

tab_report, tab_review, tab_map, tab_metrics, tab_about = st.tabs(
    ["📝 Submit observation", "🔎 Review & track", "🗺️ Map", "📊 Pilot metrics", "ℹ️ About"]
)

with tab_report:
    st.subheader("Record an environmental observation")
    st.caption("Use only synthetic or consented test information during development.")
    with st.form("nema_agora_report_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            category = st.selectbox("Observation category", CATEGORIES)
            observation_date = st.date_input("Date observed", value=date.today())
            site = st.text_input("District / site label", placeholder="e.g. Pilot site A")
            severity = st.selectbox("Initial priority (unverified)", SEVERITIES, index=1)
        with c2:
            latitude = st.number_input(
                "Latitude (optional; decimal degrees)", min_value=-90.0, max_value=90.0,
                value=0.0, step=0.0001, format="%.5f"
            )
            longitude = st.number_input(
                "Longitude (optional; decimal degrees)", min_value=-180.0, max_value=180.0,
                value=0.0, step=0.0001, format="%.5f"
            )
            evidence_reference = st.text_input(
                "Evidence reference (optional)", placeholder="Non-sensitive file name or URL"
            )
        description = st.text_area(
            "Observation description",
            placeholder="Describe what was observed, when, and from what safe/public vantage point.",
            max_chars=1500,
        )
        consent_confirmed = st.checkbox(
            "I have permission to submit this test record and have removed unnecessary personal details."
        )
        submitted = st.form_submit_button("Save pilot record", type="primary", use_container_width=True)
    if submitted:
        errors = validate_observation(
            site=site, description=description, consent_confirmed=consent_confirmed
        )
        if errors:
            for error in errors:
                st.error(error)
        else:
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            try:
                record = make_observation(
                    observation_date=observation_date,
                    category=category,
                    severity=severity,
                    site=site,
                    description=description,
                    latitude=latitude,
                    longitude=longitude,
                    consent_confirmed=consent_confirmed,
                    created_at=now,
                    evidence_reference=evidence_reference,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state.nema_agora_reports.append(record)
                st.success(f"Pilot record saved for this session: {record['case_id']}")

with tab_review:
    st.subheader("Review queue and case status")
    records = st.session_state.nema_agora_reports
    if not records:
        st.info("No pilot records yet. Add a synthetic or consented test record in the first tab.")
    else:
        selected_id = st.selectbox(
            "Select record",
            options=[r["case_id"] for r in reversed(records)],
            format_func=lambda case_id: next(
                (f"{r['case_id']} · {r['category']} · {r['status']}" for r in records if r["case_id"] == case_id),
                case_id,
            ),
        )
        selected = next(r for r in records if r["case_id"] == selected_id)
        st.markdown(f"**{selected['category']}** · {selected['severity']} priority · {selected['district_or_site']}")
        st.write(selected["description"])
        st.caption(f"Observed: {selected['observation_date']} · Created: {selected['created_at']}")
        if selected.get("evidence_reference"):
            st.write(f"Evidence reference: {selected['evidence_reference']}")
        with st.form(f"review_{selected_id}"):
            new_status = st.selectbox("Status", STATUSES, index=STATUSES.index(selected["status"]))
            review_notes = st.text_area("Reviewer notes (avoid personal/sensitive data)", value=selected.get("review_notes", ""))
            reviewed = st.form_submit_button("Update status", type="primary")
        if reviewed:
            selected["status"] = new_status
            selected["review_notes"] = review_notes.strip()
            selected["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            st.success("Status updated in this session.")
        st.divider()
        st.markdown("**All current-session records**")
        display_cols = ["case_id", "observation_date", "category", "severity", "district_or_site", "status"]
        st.dataframe(pd.DataFrame(records)[display_cols], use_container_width=True, hide_index=True)
        st.download_button(
            "Download current records as CSV",
            data=_csv_bytes(records),
            file_name="nema_agora_pilot_records.csv",
            mime="text/csv",
            use_container_width=True,
        )

with tab_map:
    st.subheader("Location view")
    geocoded = [
        r for r in st.session_state.nema_agora_reports
        if isinstance(r.get("latitude"), (int, float))
        and isinstance(r.get("longitude"), (int, float))
        and (r.get("latitude") != "" and r.get("longitude") != "")
    ]
    if not geocoded:
        st.info("No records with coordinates yet. Add decimal latitude and longitude to a test record.")
    else:
        map_df = pd.DataFrame([
            {"lat": r["latitude"], "lon": r["longitude"], "case_id": r["case_id"], "category": r["category"]}
            for r in geocoded
        ])
        st.map(map_df[["lat", "lon"]], use_container_width=True)
        st.dataframe(map_df, use_container_width=True, hide_index=True)
        st.caption("Map pins show user-entered test coordinates; they are not independently verified.")

with tab_metrics:
    st.subheader("Pilot monitoring snapshot")
    records = st.session_state.nema_agora_reports
    total = len(records)
    reviewed = sum(1 for r in records if r["status"] != "Received")
    closed = sum(1 for r in records if r["status"] == "Closed")
    complete = sum(
        1 for r in records
        if r.get("category") and r.get("observation_date") and r.get("description") and r.get("district_or_site")
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Records in session", total)
    m2.metric("Reviewed / progressed", reviewed)
    m3.metric("Closed in session", closed)
    m4.metric("Required fields complete", f"{(complete / total * 100):.0f}%" if total else "—")
    if records:
        status_counts = pd.DataFrame(records)["status"].value_counts().rename_axis("status").reset_index(name="count")
        st.bar_chart(status_counts.set_index("status"))
    else:
        st.caption("Metrics will populate when test records are created.")
    st.warning("These are prototype-session metrics only, not verified environmental outcomes or official response statistics.")

with tab_about:
    st.subheader("Project purpose")
    st.write(
        "NEMA-AGORA is a proposed student-led pilot for organising environmental observations, "
        "review status, location information and evaluation data. It is designed to complement "
        "existing environmental-management systems, not replace them."
    )
    st.markdown("**Current MVP includes**")
    st.markdown(
        "- Structured observation form and case identifier\n"
        "- Reviewer status workflow and notes\n"
        "- Optional coordinates and basic map view\n"
        "- CSV export and pilot process metrics\n"
        "- Clear prototype and data-handling limitations"
    )
    st.markdown("**Not implemented in this first MVP**")
    st.markdown(
        "- Database persistence or user authentication\n"
        "- Official NEMA, ELMIS or SWIMS integration\n"
        "- Automated enforcement or verified incident classification\n"
        "- SMS/USSD/IVR, satellite analytics, IoT or predictive models"
    )
    st.markdown("**Project links**")
    st.markdown("- [LinkedIn](https://www.linkedin.com/in/chris-shem-435166314)")
    st.markdown("- [Existing Streamlit demonstration](https://notion-live-analyzer-w6ckned7rqd4gb8oppjjke.streamlit.app/)")
    st.markdown("- [Bio-Research Enterprise Research Planner](https://sleet-spectacles-fd3.notion.site/Bio-Research-Enterprise-Research-Planner-35f9142806c6805286a5c6767a7c9cfd?pvs=143)")
