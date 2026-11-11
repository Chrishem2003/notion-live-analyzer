# Unified Platform Blueprint — Consolidation, Reliability, and Revenue

**Status:** Architecture proposal / implementation control document  
**Owner:** Chrishem / CHRISHEM platform  
**Updated:** 2026-10-22  
**Rule:** Preserve existing work. No production merge, destructive migration, secret rotation, or service replacement without evidence and an explicit change plan.

## Mission

Build a coherent, secure, revenue-capable platform from the existing projects. It should solve real user problems through reliable AI assistance, automations, research workflows, and environmental intelligence. The target is not maximum feature count; it is a small set of dependable products sharing one well-governed foundation.

## Existing product boundaries

1. **Sovereign Intelligence — shared AI/tool layer:** model/provider adapters, task routing, retrieval, tool permissions, traceable execution, evaluations, budget limits, and safe fallback.
2. **CHRISHEM AUTO-STUDIO — workflow product:** workflow definitions and versions, triggers, queues/workers, idempotency, retries, schedules, approvals, run history, connector credentials, and audit logs.
3. **Bio-Research Enterprise / Notion Live Analyzer — research product:** literature and evidence, protocols, projects, samples/data intake, analysis runs, QC gates, publication preparation, and Notion integration.
4. **NEMA-AGORA / BioEDGE — environmental product:** observations, geospatial evidence, environmental cases, compliance review, early warning, provenance, and decision-support.
5. **Shared platform services:** identity/roles, tenant boundaries, secrets, canonical schemas, API contracts, observability, billing/usage metering, configuration checks, backups, and release controls.

The current Streamlit application should remain the initial operator experience while its navigation and service boundaries are simplified. Do not prematurely rewrite it into a new frontend or split services unless measurements and deployment needs justify it.

## Current known blockers (evidence-led, not assumptions)

- Render's Streamlit service has a recorded successful deploy, while the Notion Live Analyzer API has repeated process exits with code 1.
- The API runtime logs identify missing `PLATFORM_API_KEY` and `NOTION_TOKEN` in that service's environment. Values must never be printed in logs or chat.
- Draft PR #49 (`fix/api-startup-readiness`) changes the startup script so a failed read-only optional research preflight warns rather than preventing unrelated API routes from starting. It is not merged or production-verified; tests and deployed smoke checks remain required.
- The Bio-Research workspace has overlapping blueprint/roadmap/guide/dashboard pages that need reconciliation, not another parallel set of pages.
- Existing NEMA work must be recovered from the feature branch and open PRs; historical notes indicate Phase 171 and release-readiness work, but branch/PR state must be rechecked before changing it.
- Auto-Studio must be assessed from the repository and live staging evidence. Do not infer readiness from phase labels or mocked tests alone.

## Architecture principles

- **One product shell, bounded domains:** shared navigation and identity; product modules retain explicit ownership.
- **API-first contracts:** versioned request/response schemas, consistent validation and error formats, correlation IDs, timeouts, and documented health/readiness endpoints.
- **Durable execution:** each job has a stable ID, persisted state, explicit retries/timeouts, idempotency protection, and recoverable execution history.
- **AI is not allowed to bypass governance:** models propose and explain; policy-checked tools execute. High-impact or external side effects require appropriate approval.
- **Evidence and provenance:** research claims and environmental alerts link to their source, timestamps, method, version, and uncertainty.
- **Fail closed for security:** no default admin credentials, no authentication bypasses, no exposed secrets, and no write action when authorization/configuration/validation is uncertain.
- **Synthetic-first staging:** test writes use labelled synthetic records and isolated test targets; production data and real external actions are opt-in.
- **Observability by default:** structured logs, request/run IDs, redacted secrets, metrics, and actionable errors.
- **Cost and commercial controls:** per-tenant quotas, model/provider budget ceilings, usage metering, and clear feature entitlements before public launch.
- **Accessibility and usability:** one clear home page, role-based navigation, concise working pages, useful empty/error states, and no internal implementation notes presented as end-user content.

## External code and research policy

We will learn from established projects and selectively reuse components; we will not indiscriminately copy entire repositories into the product.

Initial candidates to evaluate:
- [LangGraph](https://github.com/langchain-ai/langgraph) — stateful agent graphs, checkpointing, and human-in-the-loop patterns. Its repository LICENSE is MIT.
- [Temporal](https://github.com/temporalio/temporal) — durable workflow execution and recovery. Its repository LICENSE is MIT. Evaluate operational footprint before adoption.
- [LiteLLM](https://github.com/BerriAI/litellm) — provider abstraction/gateway, routing, and observability patterns. Its root LICENSE identifies MIT for content outside separately licensed enterprise paths; inspect the exact files and dependency licenses before reuse.
- [Haystack](https://github.com/deepset-ai/haystack) — retrieval/RAG and pipeline patterns. Its repository LICENSE is Apache-2.0.
- [Kestra](https://github.com/kestra-io/kestra) — declarative orchestration and operational UI patterns. Its repository LICENSE is Apache-2.0.
- [n8n](https://github.com/n8n-io/n8n) — useful product/connector/workflow UX reference, but its Sustainable Use License is source-available with restrictions; do not embed/resell it as a competing hosted service without a licensing review.

These are candidates, not approved dependencies. Before adopting any code: pin a commit/release; inspect the exact license and notices; check maintenance/security advisories and transitive dependencies; run secret/dependency/static scans; review data flows and telemetry; preserve required notices; document modifications; benchmark deployment/resource costs; and isolate it behind an adapter. Prefer a small dependency or documented design pattern over wholesale copying. Never execute an unknown repository's install scripts or containers directly in production.

## Delivery batches and hard acceptance gates

### Batch 1 — Establish the truth
- Inventory repositories, branches, open PRs, Render services, start commands, health endpoints, environment-variable *names*, dependency manifests, tests, and current deploy SHAs.
- Map each API/UI action to its backend route and dependency.
- Produce a red/amber/green evidence matrix; separate confirmed failures from unknowns.
- Keep secrets redacted and do not change production state during discovery.

**Exit gate:** a reproducible system map and prioritized blocker list.

### Batch 2 — Restore API service
- Fix startup so optional integration failure does not unnecessarily take down unrelated routes, while protected writes remain disabled unless configured.
- Test import/startup, liveness/readiness, missing-key behavior, unauthorized requests, and Notion preflight failure.
- Deploy to staging only after checks pass; verify actual HTTP health and logs.

**Exit gate:** API remains up; public health response exposes no secrets; protected endpoints reject missing/invalid keys; integration readiness is reported honestly.

### Batch 3 — Repair the AI brain
- Inventory all AI provider adapters, configuration keys, model names, API modules, tool registries, and error paths.
- Normalize provider calls behind a typed interface with timeouts, bounded retries, provider fallback only for eligible failures, and cost limits.
- Add deterministic mock tests plus at least one real-provider staging test when credentials are configured.
- Implement a permission-checked tool registry and trace every model/tool invocation.

**Exit gate:** one real end-to-end task succeeds; provider failure is understandable and recoverable; no fake success or unbounded retries.

### Batch 4 — Auto-Studio P0 reliability
- Audit execution path from UI/API to queue/worker and persisted result.
- Verify auth, idempotency, retries, timeouts, cancellation, dead-letter/error handling, and execution history.
- Test at least one real connector with synthetic data.
- Keep unsupported/high-risk connectors disabled.

**Exit gate:** successful run plus controlled failure/retry, no duplicate side effect, and an auditable run record.

### Batch 5 — Research lifecycle and Notion
- Choose canonical databases and archive/redirect duplicate navigation without deleting source data.
- Audit relation targets, required fields, status transitions, and workflow gates.
- Validate integration access to the correct workspace and databases.
- Run synthetic write/read-back and idempotency tests.

**Exit gate:** complete synthetic research run is linked correctly through the lifecycle and read back from the actual target.

### Batch 6 — NEMA-AGORA/BioEDGE
- Reconcile current implementation/PRs with the canonical architecture before cherry-picking or merging.
- Test UI controls and every supported workflow mode.
- Validate data lineage, geospatial calculations, thresholds, warning evidence, and human review gates.
- Clearly label demonstration/synthetic data; do not present a simulated alert as a real observation.

**Exit gate:** a reproducible end-to-end environmental demonstration with evidence, audit trail, and explicit limitations.

### Batch 7 — Productization and revenue
- Select the strongest initial customer problem and define user, outcome, pricing hypothesis, and service costs.
- Build onboarding, role/tenant boundaries, support diagnostics, usage limits, billing hooks, and terms/privacy controls.
- Test a customer journey before broadening scope.

**Exit gate:** one narrow product can be demonstrated and offered to a real target customer without manual developer intervention for every run.

## Release scorecard

A feature is marked **working** only when there is evidence for:
1. Automated tests passing.
2. A real integration/staging check where external behavior is involved.
3. Authorization and invalid-input behavior tested.
4. Logs and failure recovery verified.
5. User-facing route and instructions clear.
6. Rollback or recovery procedure documented.

Statuses: **Verified**, **Failed**, **Blocked by configuration**, or **Not yet tested**. Never use “complete” for an untested deployment.

## Immediate next actions

1. Finish review of PR #49; do not merge until its tests and deployment behavior are verified.
2. Configure the correct secrets on the API service through Render's secure environment UI; confirm presence without printing values.
3. Deploy to staging and test API health, auth rejection, and research integration readiness.
4. Re-audit the Auto-Studio and NEMA PR/branch states and inspect actual run/test evidence.
5. Add the smallest regression tests needed to prevent these failures recurring.
6. Only then move into broader AI capability work and UI consolidation.

## Change safety

No destructive cleanup of Notion pages/databases; no main-branch merge; no production migration; no wholesale vendor/framework adoption; no secret rotation; and no real-world external side effect without a specific, reviewed plan and suitable authorization. Use short-lived feature branches and reversible changes.