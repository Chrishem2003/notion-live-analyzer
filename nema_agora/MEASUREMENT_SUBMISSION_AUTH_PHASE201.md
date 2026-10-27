# Phase 201 — signed measurement submission identity dependency

## Implemented

Added `_require_measurement_submission_access` to `nema_agora/api.py`. It is a dedicated FastAPI dependency separate from the existing cross-case read dependency and:

- requires the configured platform API key;
- accepts only signed portal identities with roles `submitter`, `coordinator`, or `admin`;
- verifies the HMAC-SHA256 signature over the exact actor/role pair;
- rejects missing, too-short, or API-key-reused portal signing secrets;
- returns the trusted principal shape expected by `prepare_authenticated_measurement_submission`;
- fails closed for forged signatures and unauthorized roles.

Regression tests were added for accepted signed submitters, role rejection, role/signature mismatch, missing secret, and reused secret.

## Explicitly not enabled

This dependency is not yet attached to a POST route. The NEMA API remains read-only. No database RPC is called and no schema migration or deployment was performed. The helper only establishes a tested server-side identity boundary; it does not itself authenticate an OIDC session. The caller that creates the signature must remain trusted server-side portal code and must resolve roles from trusted bindings.

## Next release gates

1. Confirm CI for the current commits.
2. Add integration tests proving the portal client can produce this signed identity only from server-resolved session state, never request-body claims.
3. Finish review and disposable-PostgreSQL testing of migration 006, including SQL-side digest integrity and grants.
4. Only then connect this dependency, the Phase 199 adapter, and the database RPC through a guarded POST route.
