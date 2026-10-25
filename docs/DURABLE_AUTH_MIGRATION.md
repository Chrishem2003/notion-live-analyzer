# Durable authentication migration — staged plan

## Current scope

This change adds an isolated Supabase Auth client and unit tests. It is **not yet connected to the Streamlit login** and does not change production services, environment variables, user records, roles, or AI gateway settings.

## Why migration is required

- The legacy `modules/auth.py` contains simulated authentication buttons that set session state without verifying an identity.
- `modules/auth_store.py` uses local SQLite for credentials, which is not a durable identity store on a Render Free service.
- The current repository contains overlapping account/bootstrap implementations with different column names. Do not run a schema migration or delete/convert account records until the active login path and any existing records are inventoried.

## Identity contract

1. Supabase Auth owns account creation, password verification, email confirmation, token expiry and refresh.
2. Use only `SUPABASE_URL` and a public/publishable client key in this client. Never use the service-role key in Streamlit.
3. Every protected server operation must validate the supplied access token with Supabase Auth (or validate JWTs using a correctly configured trusted JWKS verifier). Never infer identity from an email field alone.
4. User identity is the stable Supabase user UUID. Email is display/contact data and can change.
5. Signup creates an ordinary user only. Admin/student roles remain server-side authorization decisions and must not be inferred from email, signup metadata, or client state.
6. Do not log passwords, access/refresh tokens, authorization headers, or provider response bodies.

## Staged rollout

### Stage A — isolated client (this change)
- Implement sign-in, sign-up and remote access-token verification with timeouts.
- Normalize returned email; require stable user ID and token.
- Handle email-confirmation-required signup without pretending the user is logged in.
- Fail closed on missing configuration, invalid HTTPS URL, network errors, invalid responses and authorization errors.
- Test request construction and failure behavior without making network calls.

### Stage B — Streamlit adapter and portal wiring (implemented behind a feature flag)
- `modules/supabase_auth_streamlit.py` renders sign-in/signup, stores the access token only in server-side Streamlit session state, and revalidates it with Supabase Auth.
- `app.py` now checks `SUPABASE_AUTH_ENABLED` on every run. The default is `false`, preserving the existing login path until an explicit rollout.
- When enabled, the portal requires a verified Supabase session and does not display or fall back to the legacy login. Invalid/expired sessions clear the portal identity.
- Supabase identities are mapped to the stable UUID plus email for the session; all newly authenticated users receive the ordinary `user` role in this integration.
- Sign-out clears the server-side token and portal identity. Tokens are not written to URLs, cookies, logs, or SQLite.
- The old bootstrap-admin and local account records have not been migrated. Do not enable the flag in production until the existing administrator is mapped through a reviewed server-side authorization design and staging tests pass.
- While Supabase mode is enabled, a Supabase-authenticated session is explicitly prevented from inheriting admin status from a matching email in the legacy SQLite table. UUID-based admin mapping remains intentionally unimplemented; all Supabase sessions stay non-admin until that separate mapping is reviewed.

### Stage C — authorization and user-data ownership
- Map existing records to stable user UUIDs using an explicit reviewed migration; do not guess by email or auto-promote roles.
- Add tenant/user ownership checks and RLS policies only after the required data model and service-role boundaries are reviewed.
- Keep server-only service-role credentials in the API service, never in the Streamlit client.

### Stage D — release gates
- Test valid, invalid, expired, unconfirmed and logged-out sessions.
- Test two independent accounts and prove one account cannot read or change another account's records.
- Verify restart/redeploy persistence and backup/restore.
- Confirm no secrets in logs, URLs, Git history or client-visible output.
- Keep `SHARED_AI_GATEWAY_ENABLED=false` until durable identity, quotas, provider connectivity and two-account isolation all pass staging tests.

## Configuration

Set `SUPABASE_URL` and either `SUPABASE_PUBLISHABLE_KEY` or `SUPABASE_ANON_KEY` through the deployment's secret/environment manager. This change intentionally does not configure deployment values or read any secret.
