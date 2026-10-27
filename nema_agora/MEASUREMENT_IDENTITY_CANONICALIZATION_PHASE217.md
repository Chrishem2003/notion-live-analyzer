# Phase 217 — reject ambiguous signed actor identifiers

## Change

The measurement submission authentication dependency now rejects actor identifiers containing carriage-return or line-feed characters before computing or verifying the HMAC identity tuple. Added focused tests for both newline forms.

This closes an avoidable ambiguity at the API trust boundary. The portal adapter already rejects newline injection; the API now independently enforces the same invariant instead of relying only on upstream behavior.

## Scope boundary

- No HTTP write route was added.
- No SQL RPC was called and no database was modified.
- The change does not replace OIDC verification, server-side role provisioning, or project/indicator authorization.
- CI must pass on the final head before this change is considered verified.
