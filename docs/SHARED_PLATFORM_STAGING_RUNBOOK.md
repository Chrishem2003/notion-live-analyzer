# Shared Platform Staging Runbook

Status: pre-release checklist. This document does not enable the gateway or authorize production deployment.

## Architecture
- Existing Streamlit/product interfaces remain the user experience.
- Render API service hosts the shared FastAPI gateway.
- Supabase Auth validates Supabase user JWTs; identity must come from a verified token, never request JSON.
- Render Key Value supplies distributed quotas. The gateway must fail closed if Redis is absent or unavailable.
- AI provider/model are selected server-side. Never point hosted Render at a developer computer's loopback address.
- NEMA spatial APIs stay disabled until a trusted server-side identity and role verifier is implemented and reviewed.

## Required server-side settings
Configure values only in the relevant Render service's environment settings. Never commit or paste secrets into chat.

- `SHARED_AI_GATEWAY_ENABLED=false` until every gate below passes.
- `AI_GATEWAY_REDIS_URL`: copy the actual connection URL from the Render Key Value dashboard only after confirming the networking path is supported. Never guess it.
- `AI_GATEWAY_RATE_LIMIT_PER_MINUTE=10` initially; supported range 1–120.
- `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` (or supported anon key) for Supabase JWT validation. Do not use a service-role key here.
- `PLATFORM_API_KEY` and `CHAT_TOKEN_SECRET` for the existing service-token flow; keep both private.
- `SOVEREIGN_AI_PROVIDER` and `SOVEREIGN_AI_MODEL` for an explicitly chosen provider/model, plus only the credential that provider needs.
- Verify the Streamlit `user_identity` is assigned only after successful authentication before relying on it for multi-user token issuance.

## Release gates
1. **CI and source:** latest-head CI must pass on both the gateway and Auto-Studio PRs. Keep PRs draft pending exact-head tests and security review.
2. **Service config:** verify API health and deployment events, configure the real Redis URL, and prove the configured provider is reachable from the API instance.
3. **Authentication:** unauthenticated, malformed, expired, or forged tokens must be rejected. Two independent users must resolve to distinct server-derived actors. Editing request JSON must not change the actor.
4. **Quota and privacy:** quota is shared across API instances; exceeding it returns 429; Redis failure blocks requests; logs exclude prompts, outputs, tokens, keys, and raw emails.
5. **Product flows:** test Sovereign Intelligence responses; Auto-Studio draft validation and catalog allow-list; Bio-Research with synthetic data first; NEMA advisory-only summaries. Repeat with two separate accounts.
6. **Release decision:** record tested commit, service, provider/model, quota behavior, and account-isolation results. If any gate fails, keep the gateway disabled.

## Project-specific safeguards
- **Auto-Studio:** AI produces proposals only. Drafts must not be executed by the gateway. Human approval and existing workflow policy remain mandatory for external side effects.
- **Bio-Research:** verify canonical Notion data-source IDs and the correct server-side Notion token before any write-back. Use idempotency and audit records for durable runs.
- **NEMA-AGORA:** do not merge the divergent integration branch wholesale. Reconcile in smaller tested changes. Do not claim live satellite ingestion, official regulatory findings, or production NEMA integration until separately verified.
- **Supabase:** NEMA tables currently have RLS enabled and no client policies. Keep access closed until explicit tenant/role policies and tests are reviewed.
- **Ollama:** `http://127.0.0.1:11434` is for a process on the same computer only. Do not expose its port publicly or configure hosted Render to use a developer PC's loopback address.

## Known blockers at this snapshot
- Render Key Value exists, but its actual connection path has not been proven reachable from the Oregon API service; the existing datastore is in Frankfurt.
- Gateway remains disabled pending configuration and staging identity tests.
- NEMA integration PR #52 is divergent and should not be merged blindly.
- Local Windows Ollama smoke testing still needs to be performed on the actual development computer.
- Notion write-back needs verified canonical source IDs and a valid server-side token.

Production enablement, database migrations, broad RLS policy changes, and live workflow execution require separate review and explicit approval.

## Audit pseudonym regression checks

The gateway test suite verifies that audit actor identifiers are HMAC-keyed with the server-side `CHAT_TOKEN_SECRET`, remain stable for the same identity and key, change when the key rotates, and become `unavailable` when the key is missing. The raw identity must not appear in the audit log. These tests are regression checks, not a substitute for verifying secret provisioning and rotation in the hosted environment.

## Shared AI token lifetime

The shared Streamlit client requests a five-minute HMAC token for each AI call. The token endpoint now accepts lifetimes from **60 to 900 seconds**, defaults to **300 seconds**, and returns the configured expiry. The platform API key remains server-to-server only. Staging must still verify that the email passed to token issuance is taken only from the server-side authenticated session, never from an untrusted form or request payload. This trusted-server assertion is not equivalent to independently validating the app user's identity; multi-user release still requires verified identity binding and two-account isolation tests.

## Verified Render region constraint (2026-10-25)

The current API web service is in **Oregon**, while the existing free Key Value instance `notion-live-analyzer-ai-rate-limit` is in **Frankfurt**. Render internal datastore URLs are for services in the same region, so do not configure the API with the internal URL as-is. See the official [Render Key Value connection guide](https://render.com/docs/key-value) and [private networking guide](https://render.com/docs/private-network).

Zero-cost-safe next steps are to verify the API service's published outbound IP ranges and evaluate a TLS external Key Value connection with a narrowly scoped allowlist, or plan a same-region datastore migration. Do not use an unrestricted external allowlist, do not guess the URL, and do not delete/recreate the existing Key Value instance without an explicit backup and migration plan. The gateway must stay disabled until the API can successfully reach the rate-limit store and the shared-quota tests pass.


## Identity issuer guard (2026-10-25)

- `SHARED_AI_GATEWAY_ENABLED=false` remains the production default.
- `SHARED_AI_LEGACY_EMAIL_TOKEN_ISSUER_ENABLED` defaults to `false`. The legacy `/api/v1/chat/token` endpoint accepts an email supplied by a trusted server and cannot independently establish the human user's identity. Do not enable this flag in production.
- New clients should send the user's actual Supabase access token to the shared gateway; the gateway validates it against Supabase Auth and derives the actor from the verified user ID.
- The legacy issuer flag exists only for isolated migration tests. Before rollout, migrate Streamlit sign-in to durable Supabase Auth (or another verified identity provider), then remove the legacy email-token issuer and its compatibility client path.
- Do not enable the shared gateway until the user identity, quota backend, provider, and two-account isolation checks have passed.
