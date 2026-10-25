# Shared Platform Staging Runbook

Status: pre-release checklist. This document does not enable the gateway or authorize production deployment.

## Architecture
- Existing Streamlit/product interfaces remain the user experience.
- Render API service hosts the shared FastAPI gateway.
- Supabase Auth validates Supabase user JWTs; identity must come from a verified token, never request JSON.
- Distributed quotas use Render Key Value when configured, or an atomic Supabase Postgres RPC as the zero-extra-infrastructure fallback. The gateway fails closed if the selected backend is absent or unavailable.
- AI provider/model are selected server-side. Never point hosted Render at a developer computer's loopback address.
- NEMA spatial APIs stay disabled until a trusted server-side identity and role verifier is implemented and reviewed.

## Required server-side settings
Configure values only in the relevant Render service's environment settings. Never commit or paste secrets into chat.

- `SHARED_AI_GATEWAY_ENABLED=false` until every gate below passes.
- `AI_GATEWAY_REDIS_URL` (preferred): use only a verified connection URL. Zero-cost fallback: review and apply `supabase/migrations/20261025000000_shared_ai_rate_limit.sql`, then set `AI_GATEWAY_SUPABASE_SERVICE_ROLE_KEY` on the API service only. Never expose the service-role key to Streamlit/browser clients, commit it, or paste it into chat. If both backends are set, Redis is selected.
- `AI_GATEWAY_RATE_LIMIT_PER_MINUTE=10` initially; supported range 1–120.
- `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` (or supported anon key) for Supabase JWT validation. Do not use a service-role key here.
- `PLATFORM_API_KEY` and `CHAT_TOKEN_SECRET` for the existing service-token flow; keep both private.
- `SOVEREIGN_AI_PROVIDER` and `SOVEREIGN_AI_MODEL` for an explicitly chosen provider/model, plus only the credential that provider needs.
- Verify the Streamlit `user_identity` is assigned only after successful authentication before relying on it for multi-user token issuance.

## Release gates
1. **CI and source:** latest-head CI must pass on both the gateway and Auto-Studio PRs. Keep PRs draft pending exact-head tests and security review.
2. **Service config:** verify API health and deployment events, configure the real Redis URL, and prove the configured provider is reachable from the API instance.
3. **Authentication:** unauthenticated, malformed, expired, or forged tokens must be rejected. Two independent users must resolve to distinct server-derived actors. Editing request JSON must not change the actor.
4. **Quota and privacy:** quota is shared across API instances; exceeding it returns 429; the selected backend failing blocks requests; logs exclude prompts, outputs, tokens, keys, and raw emails. For the Supabase option, verify the RPC is executable only by `service_role`, the table is not directly exposed, and concurrent increments are atomic.
5. **Product flows:** test Sovereign Intelligence responses; Auto-Studio draft validation and catalog allow-list; Bio-Research with synthetic data first; NEMA advisory-only summaries. Repeat with two separate accounts.
6. **Release decision:** record tested commit, service, provider/model, quota behavior, and account-isolation results. If any gate fails, keep the gateway disabled.

## Project-specific safeguards
- **Auto-Studio:** AI produces proposals only. Drafts must not be executed by the gateway. Human approval and existing workflow policy remain mandatory for external side effects.
- **Bio-Research:** verify canonical Notion data-source IDs and the correct server-side Notion token before any write-back. Use idempotency and audit records for durable runs.
- **NEMA-AGORA:** do not merge the divergent integration branch wholesale. Reconcile in smaller tested changes. Do not claim live satellite ingestion, official regulatory findings, or production NEMA integration until separately verified.
- **Supabase:** NEMA tables currently have RLS enabled and no client policies. Keep access closed until explicit tenant/role policies and tests are reviewed.
- **Ollama:** `http://127.0.0.1:11434` is for a process on the same computer only. Do not expose its port publicly or configure hosted Render to use a developer PC's loopback address.

## Known blockers at this snapshot
- Render Key Value exists in Frankfurt while the API runs in Oregon; its private connection is not a valid same-region assumption. A reviewed Supabase RPC fallback is now included in this candidate but still requires migration review/application and staging tests.
- Gateway remains disabled pending configuration and staging identity tests.
- NEMA integration PR #52 is divergent and should not be merged blindly.
- Local Windows Ollama smoke testing still needs to be performed on the actual development computer.
- Notion write-back needs verified canonical source IDs and a valid server-side token.

Production enablement, database migrations, broad RLS policy changes, and live workflow execution require separate review and explicit approval.

## Audit pseudonym regression checks

The gateway test suite verifies that audit actor identifiers are HMAC-keyed with the server-side `CHAT_TOKEN_SECRET`, remain stable for the same identity and key, change when the key rotates, and become `unavailable` when the key is missing. The raw identity must not appear in the audit log. These tests are regression checks, not a substitute for verifying secret provisioning and rotation in the hosted environment.

## Shared AI client identity migration

The gateway client helper now accepts the signed-in user's Supabase access token and sends it directly as a bearer token to `/api/v1/ai/respond`. The API validates the token against Supabase Auth and derives the actor from the verified user ID. The helper does not request an HMAC token from an email supplied by the caller and does not need the server-to-server `PLATFORM_API_KEY`.

This is a client-helper change only: do not assume the main Streamlit UI is fully migrated or that the auth adapter is enabled. Before rollout, wire the helper only to the server-side Supabase session token, confirm the token is never rendered or logged, and test sign-in, expiry, logout, and two-account isolation. Keep the gateway disabled until these end-to-end checks pass. The legacy email-token issuer remains disabled and must not be enabled in production.

## Verified Render region constraint (2026-10-25)

The current API web service is in **Oregon**, while the existing free Key Value instance `notion-live-analyzer-ai-rate-limit` is in **Frankfurt**. Render internal datastore URLs are for services in the same region, so do not configure the API with the internal URL as-is. See the official [Render Key Value connection guide](https://render.com/docs/key-value) and [private networking guide](https://render.com/docs/private-network).

Zero-cost-safe next steps are to verify the API service's published outbound IP ranges and evaluate a TLS external Key Value connection with a narrowly scoped allowlist, or plan a same-region datastore migration. Do not use an unrestricted external allowlist, do not guess the URL, and do not delete/recreate the existing Key Value instance without an explicit backup and migration plan. The gateway must stay disabled until the API can successfully reach the rate-limit store and the shared-quota tests pass.


## Identity issuer guard (2026-10-25)

- `SHARED_AI_GATEWAY_ENABLED=false` remains the production default.
- `SHARED_AI_LEGACY_EMAIL_TOKEN_ISSUER_ENABLED` defaults to `false`. The legacy `/api/v1/chat/token` endpoint accepts an email supplied by a trusted server and cannot independently establish the human user's identity. Do not enable this flag in production.
- New clients should send the user's actual Supabase access token to the shared gateway; the gateway validates it against Supabase Auth and derives the actor from the verified user ID.
- The legacy issuer flag exists only for isolated migration tests. Before rollout, migrate Streamlit sign-in to durable Supabase Auth (or another verified identity provider), then remove the legacy email-token issuer and its compatibility client path.
- Do not enable the shared gateway until the user identity, quota backend, provider, and two-account isolation checks have passed.


## Automation Studio proposal contract (2026-10-25)

The optional shared AI Streamlit surface now has a dedicated `Design an automation` mode. It calls `POST /api/v1/automations/draft`, not the general-answer endpoint. The client validates the response contract before displaying it: `status=draft_only`, `executed=false`, `approval_required=true`, a known risk level, and `requires_approval=true` for every step. If the contract is incomplete or unsafe, the UI fails closed and shows no draft. The UI presents trigger, steps, required permissions, error handling, tests, assumptions, and risk for human review.

This is still a proposal-only capability. It does not save workflows, invoke connectors, schedule jobs, or execute external actions. Tests cover bearer-token forwarding, missing-token failure, HTTPS enforcement, and rejection of a step without an approval gate.

The helper is not yet connected to the main application's verified login flow. Do not set `SUPABASE_AUTH_ENABLED=true` or `SHARED_AI_GATEWAY_ENABLED=true` in production. Complete main-app auth wiring, session expiry/logout checks, two-account isolation, provider connectivity, and quota-backend verification in staging first.


## Main-app Shared AI integration status (2026-10-25)

The main Streamlit portal now includes a **Shared AI & Automation** navigation entry behind the `SUPABASE_AUTH_ENABLED` feature flag. With the flag unset/false, the entry shows a staging-disabled message and the existing portal authentication is unchanged. With the flag explicitly enabled in an isolated staging environment, the entry uses the opt-in Supabase Auth adapter, verifies the user's token on reruns, and renders the shared AI assistant only for a verified Supabase session. The portal's sign-out path also clears any staged Supabase token.

During this migration stage, Shared AI uses a separate Supabase sign-in inside the existing portal; it does not silently convert legacy local/OAuth accounts into Supabase identities. This is intentional to avoid unsafe identity linking or accidental role inheritance. Supabase roles are resolved only from a server-side UUID allowlist; do not grant admin status based on email or user-editable metadata.

Staging procedure:
1. Deploy the feature branch only to an isolated staging service, not the production Render services.
2. Configure Supabase URL and public/publishable key for the staging service; never put the service-role key in Streamlit.
3. Keep `SHARED_AI_GATEWAY_ENABLED=false` until the gateway, quota store, and provider are verified. UI sign-in can be tested independently.
4. Set `SUPABASE_AUTH_ENABLED=true` only on that staging service, then verify sign-in, confirmation-required signup, expiry/rejected token, explicit Shared AI sign-out, portal sign-out, and session isolation.
5. Test two unrelated Supabase users and verify each actor/quota identity differs; attempt cross-account job/data access and confirm denial.
6. Do not merge or enable production until all CI and staging gates pass. This separate-login stage is not the final single-login experience.
