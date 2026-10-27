# Measurement RPC hardening — Phases 214–215

## Phase 214 — duplicate-ID rollback and table privilege regression coverage

Added PostgreSQL integration assertions for two failure boundaries:

- Reusing an existing measurement ID with a different idempotency key must fail without leaving a second idempotency record or a second audit event.
- `anon`, `authenticated`, and `service_role` must not have direct INSERT, UPDATE, or DELETE privileges on the measurement, idempotency, or audit tables. The server role retains only the required read grants and RPC EXECUTE grant.

These are tests added to the disposable-PostgreSQL suite. They are not evidence of a live database test until the CI result for the exact head is successful.

## Phase 215 — least-privilege function-owner transfer

Static review found a portability hazard in migration 006: PostgreSQL requires the target function owner to have CREATE privilege on the containing schema during an ownership transfer. Relying on default privileges for `public` is unsafe across PostgreSQL versions and project configurations.

The migration now grants `CREATE` on `public` to `nema_measurement_writer` only immediately around `ALTER FUNCTION ... OWNER TO`, then revokes it immediately. The writer remains NOLOGIN, NOINHERIT, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION, and NOBYPASSRLS, with no role memberships. A migration-contract test asserts the grant/transfer/revoke ordering.

## Validation and release boundary

- CI must pass on the final PR head before this work is considered verified.
- The PostgreSQL integration suite requires an isolated `DATABASE_URL`; skipped tests are not a pass.
- Migration 006 remains proposed and unapplied. Do not run it against shared staging or production until an explicitly approved isolated test and deployment plan exists.
- The HTTP measurement POST route remains disabled; current API behavior remains read-only.
- Evidence bytes are not yet persisted by the submission adapter, and reviewer independence remains a separate workflow gate.
- No Render service, Supabase project, secret, or deployment was changed by these commits.
