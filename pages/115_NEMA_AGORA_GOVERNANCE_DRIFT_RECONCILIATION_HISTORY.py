"""NEMA-AGORA Phase 107 — reconciliation snapshot and history demo."""
from __future__ import annotations

import streamlit as st

from nema_agora.api_governance_drift_review_reconciliation import reconcile_drift_reviews
from nema_agora.api_governance_drift_reconciliation_history import (
    build_reconciliation_snapshot,
    build_snapshot_history,
)

st.set_page_config(page_title="NEMA-AGORA Phase 107", layout="wide")
st.title("NEMA-AGORA — Governance Drift Reconciliation History")
st.caption("Phase 107 • deterministic snapshots • read-only integrity checks")
st.warning(
    "Synthetic demonstration only. This page is not an official NEMA system or integration. "
    "Snapshot integrity does not establish environmental truth, regulatory status, or enforcement authority."
)

result = reconcile_drift_reviews([], [], [], [])
first = build_reconciliation_snapshot(
    result, captured_at="2026-10-04T12:00:00Z", sequence=1
)
second = build_reconciliation_snapshot(
    result, captured_at="2026-10-04T13:00:00Z", sequence=2,
    previous_snapshot_fingerprint=first["snapshot_fingerprint"],
)
history = build_snapshot_history([first, second])

a, b, c = st.columns(3)
a.metric("Current reconciliation", result["state"])
b.metric("Snapshots in demo", history["snapshot_count"])
c.metric("History integrity", history["state"])
st.subheader("Snapshot chain")
st.dataframe(
    [
        {
            "sequence": item["sequence"],
            "captured_at": item["captured_at"],
            "state": item["state"],
            "finding_count": item["finding_count"],
            "snapshot_id": item["snapshot_id"],
            "previous_fingerprint": item["previous_snapshot_fingerprint"] or "—",
        }
        for item in (first, second)
    ],
    use_container_width=True,
)
st.subheader("History findings")
if history["findings"]:
    st.dataframe(history["findings"], use_container_width=True)
else:
    st.success("No history integrity findings in this synthetic fixture.")
with st.expander("Snapshot fingerprints"):
    st.write("Reconciliation fingerprint")
    st.code(result["reconciliation_fingerprint"])
    st.write("First snapshot fingerprint")
    st.code(first["snapshot_fingerprint"])
    st.write("History fingerprint")
    st.code(history["history_fingerprint"])
st.caption("No live operational database is connected. This demo does not persist snapshots.")
