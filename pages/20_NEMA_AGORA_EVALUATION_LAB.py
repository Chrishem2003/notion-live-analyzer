"""NEMA-AGORA Phase 13 — AI Evaluation Laboratory.

This page runs reproducible evaluation against human-labelled cases. It does
not connect an external model and does not change live case workflow.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.lab import LabCase, run_evaluation, serialise_lab_result
from nema_agora.service import NemaAgoraService
from nema_agora.shadow import DeterministicShadowAdapter
from nema_agora.storage import NemaAgoraRepository

st.set_page_config(page_title="NEMA-AGORA Evaluation Lab", page_icon="🧪", layout="wide")

st.title("🧪 NEMA-AGORA — AI Evaluation Laboratory")
st.caption("Phase 13 • reproducible measurement before model approval")

st.warning(
    "Independent student-led prototype. This laboratory evaluates advisory outputs; "
    "it is not an official NEMA evaluation system and does not submit reports to NEMA, "
    "ELMIS or SWIMS."
)

mode = mode_from_secrets(st.secrets)
principal = principal_from_streamlit_user(st.user, st.secrets) if mode == "persistent" else None
db_path = database_path_from_secrets(st.secrets) if mode == "persistent" else None
service = (
    NemaAgoraService(NemaAgoraRepository(db_path))
    if principal and principal.is_authorised and db_path
    else None
)

if not principal or not principal.is_authorised or not service:
    st.info("Authenticate in persistent mode to use the evaluation laboratory.")
    st.stop()

if not has_permission(principal.role, "intelligence:lab"):
    st.error("Your role is not permitted to run evaluation-lab jobs.")
    st.stop()

st.markdown(
    "**Purpose:** compare a deterministic baseline and later approved model adapters "
    "against human-labelled cases using the same dataset and metrics. Every run is "
    "versioned and stored separately from observation workflow data."
)

with st.expander("Evaluation contract", expanded=True):
    st.write(
        "A labelled case must contain a source record, expected category, duplicate label, "
        "optional summary-faithfulness label and a dataset slice. The laboratory rejects "
        "unsafe autonomous fields and requires source-case binding + human review."
    )
    st.code(
        json.dumps(
            {
                "case_id": "LAB-001",
                "record": {
                    "case_id": "LAB-001",
                    "category": "Solid waste / illegal dumping",
                    "description": "Synthetic observation",
                },
                "expected_category": "Solid waste / illegal dumping",
                "expected_duplicate": False,
                "expected_summary_faithful": True,
                "slice_name": "solid-waste",
            },
            indent=2,
        ),
        language="json",
    )

default_path = Path(__file__).resolve().parents[1] / "nema_agora" / "evaluation_fixture.json"
default_text = default_path.read_text(encoding="utf-8") if default_path.exists() else "[]"
dataset_text = st.text_area(
    "Human-labelled evaluation dataset (JSON)",
    value=st.session_state.get("nema_agora_lab_dataset", default_text),
    height=280,
    help="Use real, permissioned or synthetic labelled records. Do not paste personal/confidential information.",
)
dataset_version = st.text_input(
    "Dataset version",
    value=st.session_state.get("nema_agora_lab_version", "phase13-local-v1"),
    max_chars=80,
)

if st.button("Validate dataset", use_container_width=True):
    try:
        raw = json.loads(dataset_text)
        if not isinstance(raw, list):
            raise ValueError("Dataset root must be a JSON list.")
        cases = [
            LabCase(
                str(item["case_id"]),
                dict(item["record"]),
                str(item["expected_category"]),
                bool(item["expected_duplicate"]),
                item.get("expected_summary_faithful"),
                str(item.get("slice_name", "all")),
            )
            for item in raw
        ]
        if len({c.case_id for c in cases}) != len(cases):
            raise ValueError("Duplicate case_id values are not allowed.")
        st.session_state["nema_agora_lab_cases"] = cases
        st.session_state["nema_agora_lab_dataset"] = dataset_text
        st.session_state["nema_agora_lab_version"] = dataset_version
        st.success(f"Validated {len(cases)} labelled cases.")
        if len(cases) < 25:
            st.warning(
                "Fewer than 25 cases: useful for engineering checks, but it cannot "
                "pass the baseline readiness gate."
            )
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        st.error(f"Dataset rejected: {exc}")

cases = st.session_state.get("nema_agora_lab_cases", [])
st.divider()

col1, col2, col3 = st.columns(3)
col1.metric("Labelled cases", len(cases))
col2.metric("Adapters", 1)
col3.metric("External model", "Not connected")

st.info(
    "The only adapter enabled in this build is the local deterministic baseline. "
    "A real external/local model must be explicitly approved and implemented as an "
    "AdvisoryModelAdapter before it can be compared here."
)

if cases and st.button("Run Phase 13 evaluation", type="primary", use_container_width=True):
    with st.spinner("Running reproducible evaluation…"):
        result = run_evaluation(
            cases,
            {"deterministic-baseline": DeterministicShadowAdapter()},
            dataset_version=dataset_version,
        )
    st.session_state["nema_agora_lab_result"] = result
    st.success(f"Evaluation completed: {result.run_id}")

result = st.session_state.get("nema_agora_lab_result")
if result:
    st.divider()
    st.subheader("Evaluation result")
    m = result.adapters[0]
    a, b, c, d = st.columns(4)
    a.metric("Category accuracy", f"{m.category_accuracy:.1%}")
    b.metric("Duplicate F1", f"{m.duplicate_f1:.1%}")
    c.metric("Error rate", f"{m.error_rate:.1%}")
    d.metric("Mean latency", f"{m.mean_latency_ms:.1f} ms")
    st.write(
        f"Run: {result.run_id} • Dataset: {result.dataset_version} • "
        f"Readiness: {result.readiness}"
    )
    if m.confidence_brier is not None:
        st.write(
            f"Confidence Brier score: **{m.confidence_brier:.4f}** "
            f"across {m.confidence_cases} cases."
        )
    else:
        st.caption(
            "Confidence calibration not measured because the adapter supplied "
            "no valid confidence scores."
        )

    st.subheader("Per-case results")
    st.dataframe(pd.DataFrame(result.case_results), use_container_width=True, hide_index=True)

    st.subheader("Slice analysis")
    st.dataframe(pd.DataFrame(result.slice_results), use_container_width=True, hide_index=True)

    st.warning(result.safety_notice)
    st.download_button(
        "Download reproducible evaluation JSON",
        data=serialise_lab_result(result),
        file_name=f"{result.run_id}.json",
        mime="application/json",
        use_container_width=True,
    )
