# Supabase data-access and tenant-isolation audit

**Status:** read-only audit completed 2026-10-25. This document records the current database posture and the gates required before enabling user-facing access. It does not authorize a production migration.

## Observed current posture

The connected Supabase project was inspected using schema/table metadata, pg_policies, information_schema.role_table_grants, and routine grants. No data rows or secrets were read.

- public.nema_cases: RLS enabled, no policies, zero rows observed. Its primary key is case_id; there is no explicit owner or tenant UUID column.
- public.nema_case_audit: RLS enabled, no policies, zero rows observed. It is linked to nema_cases by case_id.
- public.platform_jobs: RLS enabled, no policies, zero rows observed. It has tenant_id and requested_by text fields, but no foreign keys to a trusted user/tenant identity table.
- public.platform_job_events: RLS enabled, no policies, zero rows observed.
- The inspected table grants show service_role and postgres access to these tables; no table grants were observed for anon or authenticated.
- Queue lifecycle functions (claim_platform_job, fail_platform_job, finish_platform_job, log_platform_job_queued, and redact_expired_platform_job_content) are SECURITY DEFINER and are granted to service_role and postgres in the inspected metadata. Their bodies and caller paths must continue to be reviewed before exposing any RPC surface.
- The security advisor reports four tables with RLS enabled but no policies. This is currently restrictive rather than permissive: do not “fix” the warning by adding broad USING (true) policies.

## Required access model

1. Keep browser/Streamlit clients on the public/publishable key only. The service-role key stays server-side and is never shipped to the browser or Streamlit client.
2. Authenticate each request with Supabase Auth. Resolve the stable Supabase user UUID from a verified token; do not accept user_id, tenant_id, role, or ownership as trusted merely because it appears in a client payload.
3. Keep platform_jobs and platform_job_events server/worker-only until the API has explicit enqueue, status-read, cancellation, and tenant ownership checks. A worker must derive the actor/tenant from verified server-side context, not trust caller-supplied identity fields.
4. Do not create user-level policies on nema_cases until the product's intended sharing boundary is defined (individual user, organization/tenant, or an explicitly authorized agency-wide case). The current schema lacks an owner/tenant key needed for a safe row policy.
5. Keep nema_case_audit append-only. Any future read policy must follow the parent case's verified access boundary; direct user writes/deletes should not be enabled.
6. When ownership fields and membership relations are designed, add a migration in a draft PR first. Include least-privilege grants, explicit RLS policies, and tests for anonymous denial, owner/tenant access, cross-tenant denial, and administrator scope. Review function execute grants and SECURITY DEFINER search paths as part of the same change.
7. Do not apply the migration to production until the tests run against an isolated staging database and the policy design has been reviewed.

## Release gates still open

- Verify the intended tenant model for NEMA cases and research/workspace data.
- Add an explicit user/tenant membership schema before per-user/tenant RLS is written.
- Verify API endpoints derive identity from Supabase Auth and do not trust caller-supplied ownership.
- Run two-account and cross-tenant isolation tests against staging.
- Keep SUPABASE_AUTH_ENABLED=false and SHARED_AI_GATEWAY_ENABLED=false until those gates pass.

## Audit limitations

This is a metadata/grants snapshot, not a penetration test. It does not prove the deployed API routes are correctly authorized, and it does not validate production environment variables. Re-run the advisor and policy/grant inspection after any schema or permission change.
