# Unified Platform Runtime: Security and Delivery Plan

## Purpose

Deliver one navigable platform with shared, governed services for Bio-Research Enterprise, CHRISHEM AUTO-STUDIO, Sovereign Intelligence, and NEMA-AGORA/BioEDGE. Each domain keeps its own workflows and data rules; shared infrastructure supplies identity, API boundaries, job execution, auditability, observability, and recovery.

## Verified baseline (2026-10-22)

- GitHub repository: `Chrishem2003/notion-live-analyzer`, default branch `main`.
- Render has two live services from this repository: Streamlit UI (`notion-live-analyzer`) and API (`notion-live-analyzer-api`). Both latest deployments observed in the connected Render workspace were live.
- The API includes a constant-time `X-API-Key` check and a read-only NEMA case API.
- Research-run Notion write-back is explicitly disabled in Render configuration until durable idempotency storage is available.
- Supabase project `tymqdhwomggtnsjskxuk` is active in `eu-west-1`. Its current public schema has `nema_cases` and `nema_case_audit`; both have RLS enabled and zero rows at inspection time.
- Supabase Security Advisor reports the two NEMA tables have RLS enabled but no policies. This is a deny-by-default posture for client roles, not proof that the backend is fully secure. Do not add permissive policies merely to clear the warning; the current adapter uses a server-side credential. Revisit policies only if direct end-user Supabase access is deliberately introduced.
- Authenticated Supabase reads through the deployed API, service-role credential configuration, durable backups, and live Notion write/read-back have not yet been proven end-to-end.

## Target architecture

1. **Streamlit experience** — one coherent shell with role-aware navigation and separate domain workspaces; UI is not the security boundary.
2. **Render API** — validates identity, role, request schema, resource ownership, quotas and state transitions before calling data or execution services.
3. **Supabase/Postgres** — durable source for platform job state, idempotency reservations, append-only audit events, and domain records where relational persistence is appropriate. Keep service/secret keys server-side only.
4. **Automation runtime** — enqueue, claim, execute, checkpoint, retry and recover jobs. A UI request should not directly run a long or irreversible workflow in the web process.
5. **Intelligence services** — model/provider adapters with timeouts, budget limits, evidence/source metadata, structured outputs, and human approval for consequential actions.
6. **Domain adapters** — Notion for research knowledge and workflow relations; NEMA records for environmental cases; GitHub for versioned code and review. Avoid parallel databases that duplicate the same source of truth.
7. **Observability** — health/readiness checks, correlation IDs, structured redacted logs, job metrics, failed-job queue, and operator-visible status.

## Delivery sequence and acceptance gates

### Gate A — Identity and secrets
- Inventory required environment-variable *names* and presence per service without printing values.
- Confirm one documented service-to-service authentication contract; use separate credentials for distinct trust boundaries where practical.
- Ensure no Supabase secret/service-role key, Notion token, or platform API key appears in frontend code, logs, Git history, or client-visible error messages.
- Test missing, invalid, and valid API credentials. Check role/function authorization separately from authentication.
- Keep RLS enabled and client grants least-privileged. Do not expose privileged keys to Streamlit browser components.

### Gate B — Durable shared job ledger
- Introduce versioned schema migrations for jobs, idempotency keys, attempts/leases, and append-only audit events.
- Enforce unique idempotency scope at the database level; bind each key to a canonical request hash and reject reuse with a different payload.
- Use atomic transactions for state transitions and audit records. Use optimistic version checks/leases so two workers cannot execute the same job concurrently.
- Store bounded, redacted error metadata; never store credentials in job payloads.
- Provide retention, backup/restore and recovery procedures before enabling production writes.

### Gate C — Governed automation worker
- Separate enqueueing from execution; use a background worker/queue rather than relying on a Streamlit session or web request lifetime.
- Use bounded retries with backoff, explicit terminal states, dead-letter/manual recovery, cancellation semantics, and a maximum execution budget.
- Require approval for external writes, destructive operations, public publishing, or environmental enforcement actions.
- Every execution records actor/service identity, policy decision, request hash, timestamps, outcome, and correlation ID.
- Add synthetic end-to-end tests and failure-injection tests before connecting real external side effects.

### Gate D — Domain integration
- Bio-Research: verify project/protocol/sample/data/literature relations and write a synthetic run to Notion, read it back, and verify all links.
- NEMA-AGORA: keep case access read-only until transactional audited writes, per-actor authorization, idempotency, and recovery have passed staging tests.
- Sovereign Intelligence: return source-grounded outputs with provider/timeouts/budget tracking and clear distinction between evidence and generated interpretation.
- CHRISHEM AUTO-STUDIO: expose workflow execution through the shared job contract rather than duplicating queues and audit logic.
- Do not merge or delete existing workspace data during consolidation without a verified mapping and backup.

### Gate E — Production readiness
- CI runs unit, integration-contract, authorization-negative, schema/migration, and dependency/security checks.
- Render readiness checks verify only required operational dependencies and never disclose secret configuration.
- Verify deploy rollback, backup restore, queue recovery, and monitoring alerts.
- Enable production writes only after authenticated staging succeeds and an operator can reconcile a job from request through external side effect and audit record.

## Security and reliability rules

- Deny by default; authenticate and authorize every operation at the API boundary.
- Validate caller-controlled IDs against their actual parent/tenant/workspace relations; never trust an actor name supplied in request JSON.
- Use timeouts, request size limits, pagination caps, rate limits, and allowlists for outbound integrations.
- Treat model output, webhooks, Notion content, and external API responses as untrusted data, never as executable instructions.
- Make writes idempotent and auditable; do not retry an ambiguous external write blindly.
- Keep synthetic/demo records visibly labelled and separate from real research or environmental records.
- Never claim a feature is operational solely because the page or health endpoint returns HTTP 200.

## Immediate next implementation milestone

Implement the shared durable job/idempotency/audit schema and repository contract in a reviewed branch, add authorization and concurrency tests, then connect one synthetic workflow end-to-end. Keep existing NEMA and Notion write gates closed until the staging evidence is recorded.