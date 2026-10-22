# Governance Drift Family — Contract Trace (Batch 2)

**Scope:** first source-and-test trace of the Phase 101–109 API governance drift family and its relationship to the older general-purpose Phase 49 review queue. This is a contract map, not a decision to expose APIs or merge implementations.

## Traced modules

| Module | Observed contract | Persistence / side effects | Test evidence | Runtime decision |
|---|---|---|---|---|
| `api_governance_drift.py` (Phase 101) | `detect_drift(baseline, current)`; compares selected snapshot health, coverage, source-control, finding and count fields; produces a deterministic review-triggering drift record | Pure transformation; no write | `test_api_governance_drift.py`: no drift, drift triggers review, control state elevates severity | Library contract; not an HTTP route |
| `api_governance_drift_registry.py` (Phase 102) | `GovernanceDriftRegistry.append/list`; persists drift events | SQLite; update/delete triggers enforce append-only behavior; duplicate IDs/fingerprints rejected by constraints | `test_api_governance_drift_registry.py`: append/list, duplicate rejection, immutability | Standalone persistence adapter; no runtime caller detected |
| `api_governance_drift_review_queue.py` (Phase 103) | `build_drift_review_item`, `DriftReviewQueue.enqueue/list`; queues only `REVIEW_TRIGGERED` drift | SQLite; unique drift index and append-only triggers | `test_api_governance_drift_review_queue.py`: enqueue/list, duplicate rejection, no-drift rejection | Standalone queue adapter; not a mounted API |
| `governance_review_queue.py` (Phase 49) | `build_review_queue(cases, current_snapshot)`; ranks general governance findings by severity, review need, age and dependency | Pure transformation; fingerprinted result | `test_governance_review_queue.py`: deterministic ranking, age/dependency, empty queue | **Not a duplicate** of Phase 103: different input contract and output model |
| `api_governance_drift_review_reconciliation.py` (Phase 106) | `reconcile_drift_reviews`; reconciles queue items, drift events, review audits and persisted rows | Read-only reconciliation; emits findings, does not repair records | `test_api_governance_drift_review_reconciliation.py`: valid chain, missing persisted audit, tampering, orphan/missing drift | Read-only governance library; caller not yet wired to current UI/API |
| `api_governance_drift_reconciliation_history_registry.py` (Phase 108) | `GovernanceDriftReconciliationHistoryRegistry`; stores validated sequential snapshots with predecessor binding | SQLite append-only store; rejects duplicate, broken sequence/predecessor and tampered snapshot | `test_api_governance_drift_reconciliation_history_registry.py`: persistence, sequence/predecessor and tamper checks | Distinct history store; not a duplicate of Phase 102 event registry |
| `api_governance_drift_reconciliation_monitor.py` (Phase 109) | `build_history_integrity_monitor`, `monitor_registry`; checks expected count, policies, snapshot chain, duplicate fingerprints and integrity | Read-only monitoring; explicitly no automatic repair | `test_api_governance_drift_reconciliation_monitor.py`: clean, empty, tampered and policy-mismatch cases | Monitoring/reporting library; no runtime importer detected |
| `api_governance_drift_recovery_decision_reconciliation.py` (Phase 114) | `reconcile_recovery_decisions`; checks lifecycle/decision binding, duplicates, orphan decisions and execution-gate invariants | Read-only reconciliation | `test_api_governance_drift_recovery_decision_reconciliation.py`: valid chain, orphan, tamper, duplicate | Distinct recovery-governance contract; not a general queue implementation |

## Findings

1. **The family is layered, not one repeated implementation.** Detection, event storage, review queue, review audit, reconciliation history, integrity monitoring and recovery-decision reconciliation have different inputs and invariants. Combining them based on filenames or phase numbers would erase distinct safeguards.
2. **The `api_` prefix is not proof of a mounted HTTP endpoint.** The traced functions are Python contracts and SQLite adapters; the current `api_server:app` does not import `nema_agora`.
3. **Persistence adapters are not interchangeable.** Phase 102 stores drift events; Phase 108 stores sequence-bound reconciliation snapshots. Their append-only triggers serve different records and lifecycles.
4. **Read-only monitor/reconciliation outputs must not silently repair history.** The current monitor and reconciliation contracts explicitly report findings and leave recovery to an authorized human process.
5. **Phase 104 review validation is now hardened and tested.** It validates the queue item's canonical derived ID, stable actor identifier, allowlisted role/outcome, and timezone-aware ISO review time before creating an audit record. It does not authenticate the actor or prove that the supplied role belongs to that actor; trusted server-side identity resolution remains a separate requirement.
6. **Integrity fingerprints are not authentication or signatures.** A digest can detect accidental or uncoordinated tampering only if trusted reference values are protected. It does not establish who authored a record.
7. **Phase 102 fingerprint validation is now hardened and tested.** `validate_drift` reconstructs the canonical Phase 101 payload, verifies the supplied fingerprint and derived drift ID, and rejects inconsistent state/review flags, malformed change lists, and unsupported policy versions before persistence. New tests tamper with both the payload and drift ID. This is still a library contract—not a mounted API—and the digest is not a digital signature or identity proof.

## End-to-end contract verification

Added `tests/nema_agora/test_governance_drift_chain_integration.py`. It runs the repository-level path from two governance snapshots through drift detection, append-only event storage, review queue creation, human-review audit persistence, and final read-only reconciliation. The exact-head NEMA checks and full repository CI passed at code commit `1e06490f1502d6d9a1951dbb3918ef89d4172da7`. This verifies library contracts against temporary test databases; it does not prove the hosted UI/API, OIDC, or production storage is wired.

## Safe next steps

- Phase 102 tamper tests now use valid Phase 101 outputs and reject altered changes and forged drift IDs; Phase 104 tests now reject tampered queue IDs, invalid actor IDs and timestamps without timezone offsets. Preserve these tests during future consolidation.
- Trace Phase 104/105 review-audit creation and verify actor/role binding, outcome allowlists, timestamps and digest recomputation end-to-end.
- Add an integration test for the full sequence: snapshot → drift detection → append-only event → review queue → human review audit → reconciliation. Test duplicate and tampered records at every boundary.
- Only after this chain passes should the current Streamlit page be considered as a potential consumer. No HTTP route should be exposed without a trusted authentication dependency and explicit server-side role resolution.
