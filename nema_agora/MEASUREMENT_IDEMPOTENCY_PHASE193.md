# Phase 193 — Measurement Idempotency Preflight

Status: implemented as a deterministic helper; persistence and database enforcement are not enabled.

## Added

- `nema_agora/measurement_idempotency.py` computes a SHA-256 digest over canonical JSON and classifies a supplied retry as `new`, `replay`, or `conflict` when an existing digest is available.
- `tests/test_nema_measurement_idempotency.py` checks key-order stability, changed payloads, array-order preservation, malformed/non-JSON values, unsafe keys, malformed stored digests, and retry outcomes.

## Safety boundary

This helper does not reserve idempotency keys, write data, or provide concurrency control. A database unique constraint and a single transaction covering measurement, idempotency result, and append-only audit event are still required. It must not be used as an application-only check-then-insert gate.

No Supabase migration was applied. No API endpoint or environment secret was changed. Production and staging remain untouched.
