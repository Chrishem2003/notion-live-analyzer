# Phase 199 — authenticated measurement API boundary

## What changed

- Added a framework-neutral service boundary that accepts a principal from verified authentication middleware, not identity/role fields from the measurement payload.
- It rejects unauthenticated principals, disallowed roles, and mismatches between the submitted indicator ID and the supplied registry definition.
- Added tests demonstrating that spoofed actor_id/actor_role fields in the measurement record do not override the principal claims.

## Important limitation

This is not yet wired to a deployed FastAPI/Flask endpoint, token verifier, role database, or PostgreSQL. The authenticated=true claim is meaningful only when set by trusted server-side middleware; an HTTP handler must never accept it from client JSON. This helper prepares the request only and does not execute the SQL RPC.

## Next release gates

1. Identify the repository's actual deployed API entrypoint and authentication dependency.
2. Connect the helper only behind verified authentication and enforce indicator-level scope.
3. Make the trusted API compute the digest and invoke the RPC using server credentials.
4. Execute PostgreSQL integration tests against a disposable instance.
5. Do not apply migration 006 to staging until ownership, grants, RLS, and SQL validation have been reviewed and approved.

No live database or deployment was changed.
