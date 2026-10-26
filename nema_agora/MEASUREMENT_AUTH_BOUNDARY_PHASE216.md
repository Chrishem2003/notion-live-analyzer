# Phase 216 — measurement submission identity boundary tests

## Change

Added `tests/nema_agora/test_measurement_auth_dependency.py` to exercise the existing measurement-submission authentication dependency without exposing a write endpoint.

The tests cover:

- Acceptance of a valid platform API key plus an HMAC-signed actor/role identity.
- Rejection of roles outside the submission allow-list.
- Rejection when the actor or role is changed after signing.
- Fail-closed behavior when `PLATFORM_API_KEY` is missing.
- Rejection of a signing secret that is too short or reused as the platform API key.

## Boundary preserved

The test suite calls the dependency directly. It does not create a measurement POST route, call Supabase, or write data. The current API remains read-only while the RPC and persistence gates are validated.

## Verification required

The new test file is source-level work until CI passes on the exact final commit. These tests validate the HMAC boundary, not the upstream OIDC authentication or role-provisioning implementation. Staging OIDC and signed-identity verification remain separate release gates.
