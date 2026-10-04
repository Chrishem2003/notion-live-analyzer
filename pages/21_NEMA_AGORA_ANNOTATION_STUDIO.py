"""NEMA-AGORA Phase 14 — Human Annotation & Dataset Governance."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.core import CATEGORIES
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository

st.set_page_config(page_title="NEMA-AGORA Annotation Studio", page_icon="🏷️", layout="wide")
st.title("🏷️ NEMA-AGORA — Annotation Studio")
st.caption("Phase 14 • human labels, blind review, agreement and adjudication")

st.warning(
    "Independent student-led prototype. Human annotations are research/evaluation labels; "
    "they do not establish environmental truth, illegality, regulatory status or NEMA endorsement."
)

mode = mode_from_secrets(st.secrets)
principal = principal_from_streamlit_user(st.user, st.secrets) if mode == "persistent" else None
db_path = database_path_from_secrets(st.secrets) if mode == "persistent" else None
service = NemaAgoraService(NemaAgoraRepository(db_path)) if principal and principal.is_authorised and db_path else None

if not principal or not principal.is_authorised or not service:
    st.info("Authenticate in persistent mode to use the Annotation Studio.")
    st.stop()

can_create = has_permission(principal.role, "annotation:create")
can_all = has_permission(principal.role, "annotation:read_all")
can_adjudicate = has_permission(principal.role, "annotation:adjudicate")

dataset_version = st.text_input("Dataset version", value="phase14-local-v1", max_chars=80)
observations = service.list_observations(principal)

st.info(
    "Blind annotation rule: when you label a case, the Studio does not show existing "
    "peer annotations or adjudications. This reduces anchoring and preserves independent labels."
)

if can_create:
    if not observations:
        st.info("No accessible observations are available for annotation.")
    else:
        labels = [f'{r["case_id"]} — {r["district_or_site"]}' for r in observations]
        selected = st.selectbox("Select observation to annotate", labels)
        record = observations[labels.index(selected)]

        with st.container(border=True):
            st.subheader("Evidence presented to annotator")
            st.write(f'Case: {record["case_id"]}')
            st.write(f'Observation date: {record["observation_date"]}')
            st.write(f'Site: {record["district_or_site"]}')
            st.write(f'Severity selected by submitter: {record["severity"]}')
            st.write(record["description"])
            if record.get("evidence_reference"):
                st.caption("Evidence reference supplied with the observation is shown as submitted.")

        st.subheader("Independent label")
        with st.form("annotation_form"):
            category = st.selectbox("Human category", CATEGORIES)
            duplicate = st.radio("Does the evidence indicate this is a duplicate of another case?", [False, True], format_func=lambda x: "No" if not x else "Yes")
            summary_faithful = st.radio(
                "If an AI summary is being evaluated, was it faithful?",
                [None, True, False],
                format_func=lambda x: "Not evaluated" if x is None else ("Yes" if x else "No"),
            )
            notes = st.text_area("Annotation rationale / notes", max_chars=1000)
            submitted = st.form_submit_button("Save independent annotation", type="primary", use_container_width=True)

        if submitted:
            try:
                result = service.create_annotation(
                    case_id=record["case_id"],
                    principal=principal,
                    dataset_version=dataset_version,
                    category=category,
                    duplicate=duplicate,
                    summary_faithful=summary_faithful,
                    notes=notes,
                )
                st.success(f'Annotation {result["annotation_id"]} saved. Peer labels remain hidden from this annotator.')
            except Exception as exc:
                st.error(f"Annotation rejected: {exc}")

st.divider()
st.subheader("My annotation history")
mine = service.list_own_annotations(principal, dataset_version)
if mine:
    st.dataframe(
        pd.DataFrame([
            {
                "annotation_id": x["annotation_id"],
                "case_id": x["case_id"],
                "dataset_version": x["dataset_version"],
                "category": x["category"],
                "duplicate": x["duplicate"],
                "summary_faithful": x["summary_faithful"],
                "created_at": x["created_at"],
            } for x in mine
        ]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.caption("No annotations from this account in the selected dataset version.")

if can_all:
    st.divider()
    st.subheader("Agreement & disagreement")
    agreement = service.annotation_agreement(principal, dataset_version)
    if agreement["agreement"] is None:
        st.info("At least two independent annotators are required before agreement can be measured.")
    else:
        a = agreement["agreement"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Cases compared", a["cases_compared"])
        c2.metric("Category agreement", f'{a["category_observed_agreement"]:.1%}')
        c3.metric("Category Cohen κ", f'{a["category_cohen_kappa"]:.3f}')
        st.metric("Duplicate agreement", f'{a["duplicate_observed_agreement"]:.1%}')
        if agreement["disagreements"]:
            st.warning(f'{len(agreement["disagreements"])} case(s) require adjudication.')
            st.dataframe(pd.DataFrame({"case_id": agreement["disagreements"]}), use_container_width=True, hide_index=True)
        else:
            st.success("No disagreements detected among currently stored independent labels.")

    st.subheader("Dataset readiness")
    readiness = service.annotation_readiness(principal, dataset_version)
    r1, r2, r3 = st.columns(3)
    r1.metric("Distinct cases", readiness["labelled_cases"])
    r2.metric("Double-annotated cases", readiness["double_annotated_cases"])
    r3.metric("Minimum category κ", f'{readiness["minimum_category_kappa"]:.3f}')
    st.write("Status:", readiness["status"])
    with st.expander("Readiness gates"):
        for gate, passed in readiness["gates"].items():
            st.write(("PASS" if passed else "BLOCKED") + " — " + gate)
    st.caption(readiness["safety_notice"])

    if can_adjudicate:
        st.divider()
        st.subheader("Adjudication")
        st.caption("Adjudication creates a final research label; it never overwrites the independent annotations.")
        disagreement_ids = agreement.get("disagreements", [])
        if disagreement_ids:
            case_id = st.selectbox("Case requiring adjudication", disagreement_ids)
            peer_labels = service.list_case_annotations(case_id, principal, dataset_version)
            st.dataframe(
                pd.DataFrame([
                    {
                        "annotator": x["annotator_id"],
                        "category": x["category"],
                        "duplicate": x["duplicate"],
                        "summary_faithful": x["summary_faithful"],
                        "notes": x["notes"],
                    } for x in peer_labels
                ]),
                use_container_width=True,
                hide_index=True,
            )
            with st.form("adjudication_form"):
                final_category = st.selectbox("Adjudicated category", CATEGORIES)
                final_duplicate = st.radio("Adjudicated duplicate label", [False, True], format_func=lambda x: "No" if not x else "Yes")
                final_summary = st.radio(
                    "Adjudicated summary faithfulness",
                    [None, True, False],
                    format_func=lambda x: "Not evaluated" if x is None else ("Yes" if x else "No"),
                )
                rationale = st.text_area("Adjudication rationale", max_chars=1500)
                go = st.form_submit_button("Save adjudication", type="primary", use_container_width=True)
            if go:
                try:
                    item = service.adjudicate_annotation(
                        case_id=case_id,
                        principal=principal,
                        dataset_version=dataset_version,
                        final_category=final_category,
                        final_duplicate=final_duplicate,
                        final_summary_faithful=final_summary,
                        rationale=rationale,
                    )
                    st.success(f'Adjudication {item["adjudication_id"]} saved.')
                except Exception as exc:
                    st.error(f"Adjudication rejected: {exc}")
        else:
            st.info("No disagreement is currently waiting for adjudication.")

st.divider()
st.warning(
    "Governance boundary: annotations and adjudications are labels for evaluation. "
    "They do not trigger workflow transitions, enforcement, emergency response, official reporting, "
    "or autonomous environmental decisions."
)
