# NEMA-AGORA Staging Readiness Audit — Phase 189

Date: 2026-10-27  
Integration PR: [#115](https://github.com/Chrishem2003/notion-live-analyzer/pull/115)  
Branch: `integration/nema-agora-mainline-20261026`

## Scope and safety

Read-only inspection only. No Render environment variables or secrets were changed. No Supabase migration was applied. No database rows were written. No merge or production deployment was performed.

## Observations

| Check | Result | Interpretation |
|---|---|---|
| Render staging Streamlit health | HTTP 200 after cold start | The app process responds to health checks. |
| Render staging API health | HTTP 200 | API process responds; research-run write-back reports disabled. |
| Unauthenticated NEMA case list | HTTP 503 | Fails closed because `PLATFORM_API_KEY` is not configured on the staging API. |
| Unauthenticated NEMA storage readiness | HTTP 503 | Same missing service-auth configuration; authenticated read path was not tested. |
| Supabase staging `public.nema_cases` | RLS enabled; 0 rows | Table exists, but `owner_id` is absent from the deployed schema. |
| Supabase staging `public.nema_case_audit` | RLS enabled; 0 rows | Table exists; no client-facing RLS policies are present. |
| Applied migrations | `nema_case_storage_readonly` only for NEMA | Repository migrations `002_nema_case_owner_scope.sql` and `003_nema_case_owner_integrity.sql` are not applied. |
| Security advisor | Mutable `search_path` warning for `public.reject_nema_case_audit_mutation` | Needs a reviewed, additive hardening migration before release. |
| Render staging branch | `feat/shared-ai-gateway-rebase-oct25` | Staging is not running the current NEMA integration candidate. |
| Production writes | Not performed | Remains disabled and outside this phase. |

## Code hardening in this phase

The NEMA Streamlit API client now requires an explicit `NEMA_CASE_API_BASE_URL`. It no longer silently defaults to `https://notion-live-analyzer-api.onrender.com`, which could accidentally route a staging environment to production. The example environment file now leaves the URL blank and instructs each environment to set its own endpoint.

## Blockers before authenticated staging reads

1. Configure a high-entropy `PLATFORM_API_KEY` on the staging app and staging API, with the exact same value on both.
2. Configure a separate `NEMA_PORTAL_SIGNING_SECRET` (at least 32 random characters) on both staging services. Never reuse the API key as the signing secret.
3. Set the staging app's `NEMA_CASE_API_BASE_URL` explicitly to `https://notion-live-analyzer-staging-api.onrender.com`.
4. Confirm the server-side `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set only on the API service. The service-role key must never be sent to Streamlit or committed.
5. Review and obtain explicit approval before applying `002_nema_case_owner_scope.sql` and `003_nema_case_owner_integrity.sql` to the staging project. Do not guess ownership for existing records.
6. Review a migration to pin the audit-trigger function's search path. Keep RLS enabled and do not grant direct client writes.
7. Deploy the integration candidate to staging only after an approved deployment plan, then verify signed read-only requests for an authorized role and rejection for missing/invalid signatures and unauthorized roles.

## Release decision

**NOT READY for authenticated staging reads or release.** The process health endpoints respond, but service authentication is unconfigured, the owner-scoped schema is incomplete, and the current staging services are on a different branch. Keep the PR draft, do not merge, and keep production unchanged until these blockers are resolved and recorded.
