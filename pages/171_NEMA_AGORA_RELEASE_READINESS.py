"""Phase 171 — authenticated release-candidate readiness evidence workspace."""
from __future__ import annotations

from datetime import datetime, timezone
import json

import streamlit as st

from nema_agora.access import require_permission
from nema_agora.auth import resolve_principal
from nema_agora.release_readiness import evaluate_release_readiness, validate_release_readiness_report

st.set_page_config(page_title="NEMA-AGORA Release Readiness", page_icon="🛡️", layout="wide")
st.title("NEMA-AGORA — Release Readiness")
st.caption("Phase 171 • exact-commit evidence • fail-closed release review")

principal = resolve_principal(st)
if principal is None or not principal.is_authorised:
    st.error("Authenticated, server-provisioned access is required.")
    st.stop()
try:
    require_permission(principal.role, "intelligence:pilot_readiness")
except PermissionError:
    st.error("Your role is not permitted to inspect release-readiness evidence.")
    st.stop()

st.warning(
    "This workspace checks evidence completeness for human release review. "
    "It does not deploy the application, approve production, submit to NEMA, "
    "or authorize environmental, regulatory, enforcement, or emergency action."
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
template = {
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
    st.code(json.dumps(template, indent=2), language="json")
    st.download_button(
        "Download evidence template",
        data=json.dumps(template, indent=2),
        file_name="nema_agora_release_evidence_template.json",
        mime="application/json",
    )

candidate_sha = st.text_input("Release candidate Git SHA (40 or 64 hexadecimal characters)")
observed_at = st.text_input("Assessment time (ISO 8601 with timezone)", value=datetime.now(timezone.utc).isoformat())
evidence_json = st.text_area(
    "Release evidence JSON",
    value=json.dumps(template, indent=2),
    height=360,
    help="Each required gate needs PASS, evidence_ref, a 64-character evidence_sha256, verified_at, and the exact candidate_sha.",
)

if st.button("Evaluate release readiness", type="primary"):
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
        st.table([{"gate": gate, "passed": passed} for gate, passed in report["gates"].items()])
        if report["findings"]:
            st.subheader("Findings requiring attention")
            st.dataframe(report["findings"], use_container_width=True)
        st.subheader("Fingerprint-bound report")
        st.json(report)
        st.download_button(
            "Download readiness report",
            data=json.dumps(report, sort_keys=True, indent=2),
            file_name="nema_agora_release_readiness.json",
            mime="application/json",
        )
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        st.error(f"Readiness could not be evaluated: {exc}")

st.caption(
    "A positive result means READY_FOR_HUMAN_RELEASE_REVIEW only. It is not "
    "production approval; independent human review and institutional approval remain required."
)
