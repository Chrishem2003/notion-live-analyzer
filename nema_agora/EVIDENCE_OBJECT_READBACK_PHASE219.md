# Phase 219 — verified evidence object read-back

## Delivered

The isolated Supabase Storage adapter now performs a GET after upload and verifies the SHA-256 digest of the bytes returned by storage before returning a usable object reference. A content-addressed key collision (HTTP 409) is treated as an idempotent retry only when the pre-existing object's bytes read back with the expected digest.

Regression tests cover successful upload plus read-back, digest mismatch rejection, malformed digest rejection before network activity, safe URL/bucket configuration, and a pre-existing object whose bytes must be checked.

## Remaining integration gates

- The object store is still not wired to the public measurement API or Streamlit UI.
- The database measurement RPC and audit writes remain proposed and unapplied.
- The existing measurement RPC stores evidence references and hashes in the measurement record; a database-side artifact registry and transaction-level binding between verified object keys, measurements, and audit events still needs design and PostgreSQL integration tests.
- No real Supabase bucket was accessed and no live resources were changed.
- Final-head CI and isolated PostgreSQL tests must pass before the route can be enabled.

## Acceptance criteria

1. Upload returns a reference only after read-back digest verification.
2. A mismatched read-back fails closed.
3. A database transaction binds the verified object key and digest to the measurement and append-only audit event.
4. Any database failure rolls back measurement, provenance, idempotency, and audit rows together; an uploaded but unreferenced object is an explicitly managed orphan, never a published measurement.
5. Integration tests run against an isolated PostgreSQL instance without skips.
