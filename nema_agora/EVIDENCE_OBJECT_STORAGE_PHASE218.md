# Phase 218 — isolated evidence object storage adapter

## Delivered in this phase

Added `nema_agora/evidence_object_store.py`, a server-side Supabase Storage adapter that is intentionally not wired to an HTTP route or the measurement RPC yet.

- Requires HTTPS Supabase URL, server-side service-role credential, and an explicitly configured bucket name.
- Rejects empty evidence bytes and malformed or mismatched SHA-256 digests before making a network call.
- Derives the object key from the digest rather than accepting a user-controlled path.
- Requests no-overwrite semantics and refuses to treat an HTTP 409 as proof that an existing object is valid.
- Uses bounded request timeouts and avoids returning credential-bearing errors.
- Adds mocked tests for digest validation, content-addressed paths, no-overwrite intent, unsafe configuration, and pre-existing objects.

## Important boundaries

- The adapter has not been run against a real Supabase Storage bucket; credentials and bucket configuration were not inspected or changed.
- A successful upload response is not independent evidence of authenticity, malware safety, or institutional approval.
- The database provenance reference, object read-back verification, and transactional measurement RPC integration are not implemented in this phase.
- The HTTP measurement write route remains disabled. Migration 006 remains proposed and unapplied.
- Do not claim end-to-end persistence until object upload, read-back digest verification, database reference commit, and audit event are exercised together in an isolated environment.

## Validation

The new tests are committed, but require final-head CI to pass. No live Supabase or Render resources were changed.
