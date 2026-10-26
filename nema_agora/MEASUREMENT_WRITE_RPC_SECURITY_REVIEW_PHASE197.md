# Phase 197 — PostgreSQL RPC Security Review

Status: static review completed; migration 006 remains a proposal and is **not safe to apply yet**.

## Findings that block isolated integration approval

### P1 — SECURITY DEFINER ownership is not constrained
Migration 006 creates a SECURITY DEFINER function but does not set its owner to a dedicated least-privilege role. In migration environments, the executing role may own the function or be highly privileged. The function owner also needs narrowly scoped table privileges and a deliberate RLS strategy. Do not apply the migration until the owner, grants, and RLS behavior are explicitly designed and verified in a disposable project.

### P1 — digest is supplied separately from the record
The function validates the shape of `p_payload_sha256` but does not recompute it from `p_record`. A trusted API must compute the digest from the exact canonical representation and pass the matching digest. A stronger follow-up should define one canonical serialization and verify the digest server-side (or inside PostgreSQL using a confirmed hashing extension) before accepting writes. Until that is implemented and tested, the digest is only an API assertion, not a database-proven payload digest.

### P1 — no authenticated identity inside the RPC
The function receives `p_actor_id` and `p_actor_role` as arguments. SQL cannot infer that these values came from an authenticated user. The API must derive them from its verified session/token and never copy identity or role from request JSON. This must be covered by API-level authorization tests.

### P2 — validation contract needs parity review
The function validates a subset of the application schema, not the entire Phase 191 measurement validator. Before release, compare required fields, indicator registry membership, unit matching, reporting dates/time zone, numerator/denominator arithmetic, percent bounds, and source/evidence references. Invalid date casts must return controlled validation errors, not leak implementation details.

### P2 — concurrency and rollback still unproven on PostgreSQL
The advisory lock serializes requests sharing a key, but this is not yet tested against the actual PostgreSQL version, function owner, grants, or table constraints. Test same-key/same-digest replay, same-key/different-digest conflict, duplicate measurement IDs, parallel requests, and a forced failure after each insert. Every failed transaction must leave zero partial rows.

## Required remediation order

1. Define a dedicated non-login function owner and least-privilege table grants; document RLS interaction and test as that owner.
2. Define canonical JSON digest semantics and verify the digest matches the record.
3. Bind actor identity/role to verified API authentication and enforce role-to-indicator permissions.
4. Align SQL validation with `validate_indicator_measurement` and registry rules.
5. Run PostgreSQL integration tests in a disposable environment.
6. Obtain explicit approval before staging migration application.

## Current safety boundary

Migration 006 has not been applied. No live database, environment variable, Render service, or production deployment was changed. Static CI is useful but is not evidence of successful PostgreSQL execution. The release gate stays blocked.
