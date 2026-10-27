# Phase 220 — transactional evidence provenance

## Implemented in the proposed measurement RPC

- Added a private, RLS-enabled `nema_evidence_artifacts` registry linking each artifact's bucket, content-addressed object key, SHA-256 digest, registering actor, and measurement ID.
- The RPC validates that evidence references use the strict `<bucket>/sha256/<first-two>/<sha256>` shape and that the path digest matches the declared digest.
- Artifact provenance is inserted in the same PostgreSQL function transaction as the measurement, idempotency row, and append-only audit event. A failure in any insert aborts the entire transaction.
- Direct client table privileges remain revoked. The non-login function owner gets insert-only policy access; the trusted service role gets read-only access to the registry.
- The trusted API payload adapter now requires the verified object reference returned by the storage adapter after upload/read-back validation. It no longer forwards a client-controlled evidence path into the database record.

## What this proves — and what it does not

The code binds a storage reference and digest to a measurement transaction. It does not prove evidence source authenticity, chain of custody before upload, or that the real Supabase bucket is configured. The route is not enabled, migration 006 remains proposed and unapplied, and no live storage/database resources were changed.

## Required validation before any enablement

1. Final-head repository, NEMA integration, and auth-security CI must pass.
2. PostgreSQL integration tests must run (not skip) against an isolated disposable database.
3. Tests must verify invalid object-path rejection, duplicate measurement rollback, idempotent replay, audit immutability, and rollback of measurement + artifact registry + idempotency + audit on an injected failure.
4. Staging must confirm the exact bucket is private and that upload/read-back returns bytes matching SHA-256.
5. Only after all gates pass should a separately reviewed deployment change consider enabling the API route.
