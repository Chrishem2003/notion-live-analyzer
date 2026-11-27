# Bio-Research Analysis Run Write-back

## Purpose

The Research Run write-back path links the Streamlit Research Analyzer to the private Bio-Research Enterprise workspace. It records a reproducibility entry in the private Analysis Runs register, with verified relations to project, protocol, samples, experimental-data records and source literature, plus the input dataset version.

This feature is synthetic/staging only until a live acceptance test passes. It does not approve research or validate scientific correctness.

## Components

- modules/research_run_adapter.py: Notion API data-source adapter, schema payload builder, relation-parent validation, read-back and ambiguous-write recovery.
- modules/research_run_idempotency.py: SQLite ledger with stable run IDs and payload fingerprints.
- api_server.py: authenticated POST /api/v1/research-runs.
- modules/research_run_client.py: Streamlit-facing API client with no automatic POST retry.
- pages/09_Integrations_Hub.py: Bio-Research Runs tab.

## Required server-side environment

Set these values in the API deployment's secret/environment configuration. Never commit actual credentials.

- PLATFORM_API_KEY: high-entropy service-to-service secret.
- NOTION_TOKEN: Notion integration token with access only to the required private research sources.
- NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID: private Analysis Runs data source.
- NOTION_PROJECTS_DATA_SOURCE_ID: private Project Master data source.
- NOTION_PROTOCOLS_DATA_SOURCE_ID: private Protocol Register data source.
- NOTION_SAMPLES_DATA_SOURCE_ID: private Sample Collection data source.
- NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID: private Experimental Data Engine data source.
- NOTION_LITERATURE_DATA_SOURCE_ID: private Literature data source used to validate source-evidence page IDs.
- RESEARCH_RUN_IDEMPOTENCY_DB: absolute path to a persistent SQLite file. All API workers must share the same file on storage that supports SQLite locking.

For the **full relation-graph preflight**, also configure these private source IDs in the API environment:
- NOTION_GENOMIC_SEQUENCE_DATA_SOURCE_ID: private Genomic Sequence Log source.
- NOTION_TASKS_DATA_SOURCE_ID: private Daily Task source.
- NOTION_BRAIN_NOTES_DATA_SOURCE_ID: private Brain Notes source.

The API endpoint writes only to Analysis Runs, validates the parent data source for project/protocol/sample/data/evidence pages, and stores linked Source Evidence plus Input Dataset Version. The extra three IDs let the preflight check the rest of the connected private graph, including project-task and genomic-sequence links.

Use the exact private source IDs shown by the Notion data-source schema. Configure each value using the data-source schema in the **private Bio-Research Enterprise** workspace. Do not copy IDs from the published template, and do not commit private workspace IDs or credentials into this repository.

| Environment variable | Required source |
|---|---|
| `NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID` | Private Analysis Runs — Reproducibility Register |
| `NOTION_PROJECTS_DATA_SOURCE_ID` | Private Project Master |
| `NOTION_PROTOCOLS_DATA_SOURCE_ID` | Private Protocol Register |
| `NOTION_SAMPLES_DATA_SOURCE_ID` | Private Sample Collection |
| `NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID` | Private Experimental Data Engine |
| `NOTION_LITERATURE_DATA_SOURCE_ID` | Private Literature |
| `NOTION_GENOMIC_SEQUENCE_DATA_SOURCE_ID` | Private Genomic Sequence Log |
| `NOTION_TASKS_DATA_SOURCE_ID` | Private Daily Task |
| `NOTION_BRAIN_NOTES_DATA_SOURCE_ID` | Private Brain Notes |

The preflight fails closed if these IDs point to the wrong relation graph. Re-fetch the data-source schema and verify the ancestor path before changing the environment values.

Start the API in a trusted deployment only after environment variables and the read-only preflight are ready:

    sh scripts/start_research_run_api.sh

Put the API behind HTTPS and network controls before exposing it outside a trusted environment. For real research, do not use a per-container ephemeral SQLite path or multiple replicas with separate ledgers.

## Input integrity gates

Before the endpoint writes a run, it validates not only each page's parent data source but also the relationships between the selected records:
- The selected Project must be classified `Demo` or `Synthetic/Test`.
- The selected Protocol must already relate to the chosen Project; a protocol linked to another project or with a missing Project relation is rejected.
- Each selected Sample must already relate to the chosen Project and Protocol and be classified `Demo` or `Synthetic/Test`.
- Each selected Experimental Data record must already relate to the same Project and Protocol, link to at least one Sample selected for the run, and be classified `Demo` or `Synthetic/Test`. Data records cannot be submitted without at least one selected Sample.
- Each supplied Source Evidence page must belong to the private Literature source and be classified `Demo` or `Synthetic/Test`.
- The selected dataset version and source-evidence page IDs are stored on the run and included in its deterministic manifest fingerprint. The API recomputes the SHA-256 manifest from submitted inputs and rejects a client-supplied mismatch; the UI does not accept a manually entered hash.

Invalid or incomplete relationships return HTTP 422 before the Analysis Runs record is created. This is intentional: the current three Demo samples have missing Project and Protocol links, so they must be mapped by a human before they can be used as run inputs. Do not bypass the gate or infer the intended mapping from names.

## Deployment inventory and separate API service

The Render blueprint now declares a separate `notion-live-analyzer-api` service, health-checks it at `/api/v1/health`, and starts it through `scripts/start_research_run_api.sh`. That startup script runs the read-only schema/relation preflight before starting Uvicorn; a mismatch or missing source ID stops the API from starting. The Streamlit service points to `https://notion-live-analyzer-api.onrender.com` by default. Confirm the actual Render service hostname after Blueprint sync.

**The free-tier blueprint is synthetic staging only.** It opts into an ephemeral SQLite ledger under `/tmp` because free service disks are not persistent. Never use this deployment for real research, regulated data, or production-grade idempotency. Before any real-research workflow, use an appropriate plan with persistent storage mounted at `/var/data`, set `RESEARCH_RUN_IDEMPOTENCY_DB=/var/data/research_run_idempotency.sqlite3`, and set `RESEARCH_RUN_ALLOW_EPHEMERAL_LEDGER=false`. Do not create paid resources without reviewing their cost.

Set `PLATFORM_API_KEY` to the same high-entropy value on both the Streamlit and API services. Set `NOTION_TOKEN` and all nine private data-source IDs only in the API service's Render dashboard. These values are marked `sync: false` in the Blueprint and are intentionally absent from Git. The API integration token should have access only to the required private sources.

The API endpoint is protected by `X-API-Key`; keep the key server-side. Authentication rejects missing, mismatched, whitespace-only, or duplicate `X-API-Key` headers; a blank/whitespace-only server key fails closed. Nonblank keys are compared exactly without trimming. Do not expose the key in browser code or paste it into Streamlit inputs.

## Required Streamlit environment

- RESEARCH_RUN_API_URL: base URL of the private API service, e.g. https://api.example.org.
- PLATFORM_API_KEY: same service secret configured on the API host.

Keep these in deployment secrets, not in the Streamlit page or source code. The new UI is intentionally disabled when either is absent.

## Preflight before starting the API

Run this from the repository root after setting the API service environment variables and mounting the persistent disk:

    python scripts/research_run_preflight.py

The command performs read-only GET requests against nine configured private Notion data sources. It checks required properties and validates 23 relation edges across Analysis Runs, Project Master, Protocols, Samples, Experimental Data, Literature, Genomic Sequence Log, Daily Tasks and Brain Notes. It also initializes the SQLite idempotency ledger at the configured absolute path to verify that the mounted directory is writable. It does not create or modify any research records.

A successful result means the configured schema graph and local ledger path are ready for a synthetic staging test; it does **not** prove the API is reachable from Streamlit, that all workers share the same disk, or that a live research run can be persisted. Keep the service on HOLD until the staging checklist below passes.

## Staging acceptance checklist

1. Confirm Notion integration access to all nine private data sources.
2. Confirm the source IDs above point to private workspace data sources, not template sources.
3. Run the read-only startup preflight. The free Render blueprint is for synthetic staging only and explicitly uses an ephemeral ledger; use persistent shared storage before any real-research workflow.
4. Open Integrations Hub → Bio-Research Runs in Streamlit.
5. Submit a synthetic test with private Project and Protocol page IDs and optional private Sample/Data page IDs.
6. Confirm the returned Notion URL opens the new Analysis Run and the linked relations point to the intended private records.
7. Submit again with the exact same run ID and payload. It must return the existing page rather than create a duplicate.
8. Change the payload while keeping the same run ID. The API must return a conflict.
9. Simulate an ambiguous write/timeout. A retry must use the same run ID and reconcile read-only; it must not create a second page if no match is visible.
10. Verify run state remains Draft / Intake / Pending QC / Not Checked / Synthetic/Test until a human reviewer completes the workflow.

## Repeatable synthetic acceptance runner

Use `scripts/research_run_staging_smoke.py` after the API is deployed and the read-only preflight passes. The default command is a dry run and sends no requests. The execution mode performs three authenticated calls: initial synthetic run, exact same-ID/same-payload retry (must reuse the page), and changed-payload/same-ID retry (must return HTTP 409). The synthetic Analysis Run is retained as acceptance evidence and is not automatically deleted.

Configure these values in your local shell or trusted runner, never in Git or ChatGPT messages:
- `RESEARCH_RUN_API_URL`: HTTPS base URL of the staging API.
- `PLATFORM_API_KEY`: same secret configured on the Streamlit/API services.
- `RESEARCH_RUN_SMOKE_PROJECT_PAGE_ID`: verified private Demo project page ID.
- `RESEARCH_RUN_SMOKE_PROTOCOL_PAGE_ID`: verified private draft protocol page ID whose existing `Project` relation points to the selected Demo project.
- `RESEARCH_RUN_SMOKE_CONFIRM_SYNTHETIC=true`: explicit confirmation that this is a synthetic staging test.

First run the dry run:

    python scripts/research_run_staging_smoke.py

Then execute only with a recorded stable run ID:

    python scripts/research_run_staging_smoke.py --execute --run-id staging-smoke-YYYYMMDD-001

If the response is ambiguous, reuse the exact same `--run-id`; do not create a new ID until the prior attempt is reconciled. The script requires HTTPS, uses no sample/data/evidence records, and stops unless the protocol already belongs to the selected project and the returned classification and workflow gates remain Synthetic/Test / Draft / Intake / Pending QC.

## Recovery behavior

- 401: API key missing or invalid.
- 503: API configuration missing or write outcome is ambiguous.
- 409: run ID is already in progress or has been reused with a different payload.
- 422: invalid request data.
- 502: Notion rejected the request, relation parent validation failed, or read-back failed.

After a timeout, reuse the same run ID. Do not mint a new ID until the prior attempt is reconciled. An ambiguous reservation intentionally fails closed when no matching Notion record is visible; an operator must inspect Notion and reconcile the ledger before clearing it.

## Current status

The adapter compares the submitted Run Manifest Hash with an existing Analysis Run before returning it as an idempotent retry. This check applies to direct existing-record lookup, timeout recovery, ambiguous-write recovery, and completed-ledger read-back. A reused External Run ID with a missing or different manifest is rejected for manual reconciliation rather than silently returning a record for different inputs. This protects against a reset or lost local ledger but does not replace persistent storage or live acceptance testing.

The automated tests cover the adapter, ledger, API authentication/configuration, relation validation, client behavior, manifest fingerprinting and UI syntax. These tests use mocks and do not prove that the deployed service can authenticate to Notion. PRs #25 and #32–#36 are merged; the PR-head CI runs for #33, #34, #35 and #36 passed. The retry path now verifies manifests on direct lookup, timeout recovery, ambiguous recovery and completed-ledger read-back, with an API test asserting HTTP 409 on mismatch. The Render Blueprint no longer includes a billable keepalive cron. No Render Blueprint sync, authenticated live Notion write, or deployment acceptance test has been completed.


## Ledger path preflight hardening — 2026-11-22

Before any Notion schema request or SQLite ledger initialization, the preflight now normalizes the configured absolute path and classifies ephemeral roots using the normalized path. It inspects every parent path component with `lstat` and rejects symlinks or special paths. If the ledger file already exists, it must be a regular single-link file; symlinks, special files, and hard-linked aliases fail closed. The checks do not write to a rejected target and do not create the ledger until the later explicit initialization step.

Regression coverage uses only temporary synthetic paths and mocked Notion HTTP:
- symlinked parent/ancestor is rejected before any Notion request;
- symlinked ledger file is rejected and its target bytes remain unchanged;
- hard-linked ledger file is rejected and the original target remains unchanged;
- dot-segment normalization prevents an ephemeral path from bypassing the storage-root gate;
- a directory at the ledger filename is rejected as non-regular.

These `lstat` checks are defense in depth, not an atomic guarantee against a concurrent path replacement. Keep the ledger parent owner-controlled and non-writable by untrusted principals. They do not prove persistent-disk durability, cross-host SQLite locking, backup/restore, or managed-host ACL correctness.

### Current Free-tier configuration correction

This note supersedes the older free-tier paragraph above that says the blueprint opts into an ephemeral `/tmp` ledger. At the currently inspected staging-branch revision, `render.yaml` configures `RESEARCH_RUN_IDEMPOTENCY_DB=/var/data/research_run_idempotency.sqlite3`, `RESEARCH_RUN_ALLOW_EPHEMERAL_LEDGER=false`, and `RESEARCH_RUN_WRITEBACK_ENABLED=false`. The API startup script runs the read-only preflight only when write-back is explicitly enabled; otherwise it starts with research-run write-back disabled. The Render service metadata reports the staging API as Free, and the blueprint comments that Free does not provide the required persistent disk. Do not infer that the configured `/var/data` path is mounted or durable. Real research write-back remains disabled until a suitable persistent store and restore acceptance are independently verified.


### Parent directory access requirement

The preflight requires the existing ledger parent directory to be both writable and searchable (os.W_OK | os.X_OK) before any Notion schema request. Regression tests cover a symlink in an ancestor component and a parent that fails the combined access check; both must fail before HTTP calls or ledger creation.


### Preflight path revalidation and diagnostic-output minimization

After all nine Notion data-source schemas and the 23 relation edges are checked, the preflight revalidates the configured ledger parent and existing ledger file immediately before opening SQLite. This catches a parent symlink or special-path substitution that occurs during the remote schema requests. It narrows the time-of-check/time-of-use window but is not an atomic directory-handle guarantee; the parent must remain owner-controlled and managed-host ACL/mount acceptance is still required.

Successful preflight output no longer prints the absolute idempotency database path. It reports only that a path was configured and the storage classification. Treat filesystem paths and mount layout as operational metadata; do not put them in shared logs or public diagnostics.

Synthetic regression coverage replaces the ledger parent with a symlink during the ninth mocked schema request and confirms the final revalidation rejects it before SQLite creates a file in either the moved or replacement directory. A separate assertion verifies the successful result contains neither the absolute ledger path nor its parent.


### Synthetic staging smoke-runner failure-path contract

The offline test suite for `scripts/research_run_staging_smoke.py` now exercises both the successful three-call sequence and fail-closed behavior: non-200 initial response, mismatched run ID, non-synthetic classification, retry returning a different page, changed-payload response other than HTTP 409, malformed JSON, request timeout without automatic retry, and the explicit `RESEARCH_RUN_SMOKE_CONFIRM_SYNTHETIC=true` execution gate. Fixtures use an in-memory fake HTTP session; no network request or Notion record is created by these tests.

The focused preflight workflow includes the smoke-runner test module and compiles the runner. This verifies the acceptance harness contract only; it does not substitute for the owner-authorized live synthetic staging acceptance described above.


### Synthetic smoke-runner transport boundary

The staging smoke runner treats its configured API URL as an explicit trust boundary. It requires an absolute HTTPS URL, rejects embedded URL credentials, query strings, fragments and malformed ports, and sends every request with automatic redirects disabled. Any 3xx response fails closed before a second request is made. This prevents the runner's custom `X-API-Key` header from being forwarded by an HTTP client to a redirect destination.

The offline contract tests cover credential-bearing URLs, query/fragment URLs, invalid ports, redirect rejection, and the `allow_redirects=false` request option on the normal three-call synthetic sequence. These tests use a fake session and do not contact staging. They do not prove DNS ownership, TLS certificate policy, network egress restrictions, or the actual deployed API endpoint; those remain part of owner-authorized staging acceptance.

### Service API-key authentication contract

The research-run route uses a dependency-free service API-key verifier. An unset server key fails closed as service-unavailable; a missing or mismatched client key is unauthorized; an exact match is checked with `hmac.compare_digest`. Unsupported string encodings are treated as an invalid key rather than an unhandled comparison error. The FastAPI dependency maps these verifier outcomes to the existing HTTP 503 and 401 responses.

Focused synthetic tests exercise an unconfigured server key, missing/empty client key, wrong key, non-ASCII input, and the constant-time comparison call. They do not require live credentials or call Notion. Host/Origin allowlisting and trusted-proxy forwarded-header policy remain intentionally unconfigured until the owner supplies the approved hostnames and proxy topology; do not infer or trust forwarded headers from a request.

## API route authentication contract — 2026-11-25

The focused safety workflow now has a separate `api-auth-contract` job that installs the dedicated API runtime dependencies from `requirements-api.txt` and runs the actual FastAPI research-run endpoint contract suite. This is separate from the dependency-light verifier tests so route-level HTTP behavior is tested without importing the full API into the minimal preflight job.

The endpoint suite includes explicit negative-path checks for:
- missing `X-API-Key` (HTTP 401);
- incorrect synthetic `X-API-Key` (HTTP 401, and neither the supplied nor configured test key is echoed);
- unconfigured server `PLATFORM_API_KEY` (HTTP 503, and the supplied synthetic key is not echoed).

The tests use synthetic keys and fixture-only configuration. The pytest fixture enables `RESEARCH_RUN_WRITEBACK_ENABLED=true` only to reach the endpoint logic; every test that reaches persistence replaces the adapter/ledger with fakes, while failure-path tests stop before external I/O. No live Notion requests or real credentials are used. They verify the route's FastAPI dependency mapping; they do not verify the deployed proxy/Host policy, live secret configuration, DNS/TLS ownership, or staging authentication. Host/Origin and forwarded-header policy remains blocked until the owner supplies the approved hostnames and proxy topology.


The first API-contract workflow run exposed that the shared test fixture did not set `RESEARCH_RUN_WRITEBACK_ENABLED`, so several pre-existing endpoint tests stopped at the safe-mode gate before exercising their intended validation paths. The fixture now enables that flag only for the isolated test process; persistence-reaching tests use fake adapters/ledgers. This is a test-fixture correction, not a deployment/environment change.


## Credential-bearing HTTP redirect protection — 2026-11-26

A read-only route/client inventory found server-side HTTP calls that attach bearer, API-key, publishable-key, or Supabase service-role headers while leaving Requests' redirect behavior at its default. A redirect can move a credential-bearing request to an unintended endpoint; custom headers such as `apikey` or `X-API-Key` are not guaranteed to be stripped by the HTTP library.

The isolated hardening candidate disables redirects for Notion schema preflight; Notion Analysis Run query/read/create; the research-run API client; Supabase durable platform-job and NEMA repositories; Supabase user-token verification in per-user jobs and shared AI; and the shared-AI Supabase rate-limit RPC. Unexpected 3xx responses fail closed. No redirect target is contacted. Host allowlists, DNS/TLS trust, proxy configuration, credentials, environment values, and provider selection are unchanged.

A new synthetic fake-session regression module covers all eight client paths and asserts `allow_redirects=False`, one request only, and safe rejection of HTTP 302. Tests do not contact Notion, Supabase, AI providers, or deployed services. This is transport-contract evidence only; DNS ownership, TLS validation, egress policy, and live service identity remain separate gates.

The route inventory confirmed: NEMA exposes read-only case GETs; Sovereign Intelligence exposes provider listing and a governed solve POST behind the platform service key; platform-jobs exposes service-owned enqueue/status routes plus an opt-in Supabase-user-scoped API; shared AI exposes bearer-authenticated response/draft routes and uses Redis or a server-side Supabase RPC for rate limiting. The user-scoped API is not mounted unless `USER_JOB_API_ENABLED` is explicitly enabled. Service-key routes are not end-user identity and must remain server-side.


## Raw request-header ambiguity protection — 2026-11-26

The API boundary now rejects repeated raw authentication and idempotency header fields before any protected operation:

- Core research-run, durable service-job, NEMA case, and Sovereign Intelligence service-key guards require exactly one raw `X-API-Key` field. The core research-run guard already enforced this; the shared service-router guards now use the same contract.
- Shared AI and opt-in per-user job routes require exactly one raw `Authorization` field before bearer-token verification.
- Service-owned and per-user job creation require exactly one raw `Idempotency-Key` field. Duplicate values are rejected with HTTP 400 before repository construction; a missing required key retains FastAPI's existing required-header validation behavior.
- Authentication duplicates fail closed with HTTP 401. Header values are never included in error details.

The shared helper reads `Request.headers.getlist()`, so it detects repeated fields that reach the ASGI application. An upstream proxy that combines repeated fields into one value must enforce equivalent duplicate-header rejection at ingress; this code does not prove proxy behavior.

Route-level regression tests use synthetic duplicate fields and fake/disabled external dependencies. They cover the core API, platform jobs, Sovereign Intelligence, NEMA, shared AI, per-user jobs, and both job-creation idempotency boundaries. No real credential, Supabase request, Notion request, AI-provider call, repository write, or research record is used.

This is an application-boundary contract only. It does not establish the owner-approved Host/Origin policy, trusted-proxy configuration, DNS/TLS identity, ingress normalization behavior, or deployed runtime configuration. Keep research-run write-back disabled and Production HOLD.


## Webhook header ambiguity protection — 2026-11-26

A follow-up read-only audit of `api_server.py` found two additional inbound GitHub webhook headers whose repeated raw fields could create ambiguous request interpretation:

- `X-Hub-Signature-256` now requires exactly one raw field and is compared against the parsed FastAPI header before HMAC verification.
- `X-GitHub-Event` may be absent (preserving the existing `unknown` behavior) or appear exactly once. Multiple event fields are rejected with HTTP 400 before payload routing.

Two route-level tests use a synthetic webhook secret and body: duplicate identical valid signature fields must return HTTP 401; duplicate event fields must return HTTP 400. No GitHub webhook, Celery task, RAG ingestion, or external request is executed by these tests.

This is application-side duplicate-field handling only. It does not establish upstream proxy normalization, GitHub delivery authentication in the deployed environment, webhook replay protection, or DNS/TLS/Host policy. Keep production integrations and research-run write-back unchanged.


## WebSocket token query ambiguity protection — 2026-11-26

The remaining API-boundary audit found that chat, collaborative-document, and meeting WebSockets authenticate with a `token` query parameter. FastAPI's scalar parameter can select one value when a URL contains repeated `token` fields.

All three WebSocket routes now inspect `websocket.query_params.getlist("token")` before token verification and close with application code 4401 unless exactly one query value is present and it matches the parsed parameter.

Three route-level TestClient WebSocket cases use repeated identical synthetic tokens and patch token verification to fail if called. They verify that ambiguous tokens are rejected before authentication or any chat/document/meeting backend is touched.

This does not remove the existing query-token design or prevent tokens from appearing in URL/access logs; it only rejects repeated query fields. A future transport review should assess moving WebSocket authentication to a short-lived, single-use handshake ticket or another owner-approved mechanism. No real token or live WebSocket session was used.


## Legacy chat-token issuer query ambiguity — 2026-11-26

The remaining identity-bearing query audit found that the service-key-protected legacy chat-token issuer accepted scalar `email` and `ttl_seconds` query parameters without checking for repeated values. Although the issuer is disabled by default, a controlled environment that explicitly enables it should not rely on ambiguous query selection.

The route now requires exactly one `email` query value and allows at most one `ttl_seconds` value before checking the legacy-issuer enable flag. Duplicate identity/TTL fields return HTTP 400 without invoking token issuance. Two synthetic route-level tests patch `chat_auth.issue_chat_token` to fail if called, proving the rejection occurs first.

This does not change the default disabled state, issue any real token, or prove Host/proxy/ingress behavior. The legacy email issuer still cannot independently establish which human is authenticated; keep it disabled until a separate approved identity migration.



## Batch 166 — dormant legacy API entrypoint inventory and deployment-manifest guard (2026-11-27)

**Status:** implementation committed; static manifest contract must pass exact-head CI. No runtime or deployment claim is made.

### Read-only inventory and findings

The complete Git tree for the feature branch was read, then the active checked-in Render/Docker startup chain and the remaining standalone FastAPI modules were inspected.

- The checked-in Render Streamlit service selects `Dockerfile`, whose command starts `streamlit run app.py`.
- The checked-in Render API service selects `Dockerfile.api` and `scripts/start_research_run_api.sh`; the script starts `uvicorn api_server:app`.
- The API startup script runs the research-run preflight only when `RESEARCH_RUN_WRITEBACK_ENABLED=true`; otherwise it prints that write-back is disabled and starts the API without enabling research-run writes.
- The checked-in Render manifest explicitly sets `RESEARCH_RUN_WRITEBACK_ENABLED=false` and `RESEARCH_RUN_ALLOW_EPHEMERAL_LEDGER=false`.
- The deployed API entrypoint includes the previously audited NEMA, Sovereign Intelligence, platform-jobs, per-user jobs, and shared-AI routers. This inventory does not prove live deployment state.

Two separate legacy ASGI modules are present but are not selected by the checked-in Render/Docker startup configuration:

1. `fastapi_app.py` declares a standalone Multi-Problem Solver FastAPI application. Its task dispatch, task listing/status, agent-run, and RAG index/query routes have no authentication dependency in the inspected source. It also configures wildcard CORS with credentials enabled. If launched independently, those routes require a separate authentication, authorization, CORS, and data-classification review.
2. `api_gateway.py` and the byte-identical `modules/api_gateway.py` expose `/logs` and `/sessions` without an authentication dependency and return local system-log/session records. They are not selected as Render/Docker startup entrypoints in the checked-in manifest.

These are **dormant/unverified legacy entrypoints**, not proven unreachable. The checked-in deployment configuration is not evidence about other manually configured services, local launches, or external hosting. Neither module was modified or launched in this batch.

### Implementation

Added `tests/test_deployment_entrypoint_guard.py` with three static configuration regression tests:

- The Render manifest selects only the reviewed Streamlit and research-run API service entrypoints.
- The Streamlit Docker image starts `app.py`, not either legacy ASGI module.
- The API Docker image uses the guarded startup script, which starts `api_server:app`, and the checked-in write-back/ephemeral-ledger flags remain false.

Updated `.github/workflows/research-run-preflight-safety.yml` to include the new test in the preflight-safety job and to trigger on changes to the deployment manifest, Dockerfiles, startup script, test, and runbook.

This is a **static deployment-manifest guard**. It does not exercise a live Render container, prove that dashboard settings match the manifest, or establish that the legacy modules cannot be launched through another service definition.

### Changed items and source read-back

- `tests/test_deployment_entrypoint_guard.py` — created; initial blob `7b2640d9e661b3d90654dad6dfbddd7a110862ea`
- `.github/workflows/research-run-preflight-safety.yml` — updated to run the guard and watch deployment-entrypoint paths; commit `9ee89a2cccf6c295f6cd33ccbdcbd46dbff9787c`, blob `6c20c7c0f240ec101f1e51045a51951326766fcb`
- `docs/research-run-writeback.md` — this additive audit record

The original source files `fastapi_app.py`, `api_gateway.py`, and `modules/api_gateway.py` were left unchanged. No secrets, environment values, credentials, services, permissions, or deployment settings were changed.

### Functional verification and limits

**Final exact-head CI accepted:** PR run [46001070422](https://github.com/Chrishem2003/notion-live-analyzer/actions/runs/46001070422), merge commit `2e754a9afc321df4c5b` with head `9273e4b39045e488f1a7835ef57beb94b6a41ad4`: preflight-safety passed 47 tests (including all three new deployment-entrypoint guard tests), API-auth-contract passed 45 tests, both with zero failures/skips and successful compilation. Both job records, steps, and raw logs were inspected. This confirms only the checked-in static deployment configuration; it does not prove live runtime exposure or security.

### Blockers

- Owner decision is required before either legacy API is hardened for a supported deployment or formally retired from use. Do not launch either module in a public environment meanwhile.
- Owner-approved Host/Origin and reverse-proxy topology is still required before ingress trust policy changes.
- Owner-authorized read-only access to the staging runtime is still required for service identity, ACL, mount, persistence, restart, and synthetic restore acceptance.
- Authenticated live Notion synthetic create/read-back/replay, shared outbox, cross-host execution, tenant isolation/RLS, worker leases, HMAC custody, backup ownership/retention, and independent scientific QC/reproducibility/ethics approvals remain outstanding.

### Rollback

On the isolated feature branch, revert the Batch 166 workflow update commit `9ee89a2c` and then the new test-file commit `3ac59348`. The runbook append can be reverted as its own later commit. No production rollback is required; no deployment occurred.

### Next exact action

Obtain an owner decision for the two dormant legacy API entrypoints: either authorize a separately scoped hardening design with explicit authentication/authorization and CORS requirements, or confirm they are not supported deployment targets and authorize a retirement plan. Until that decision, keep them unlaunched. In parallel, obtain owner-approved Host/proxy topology and owner-authorized read-only staging runtime access. Keep research-run write-back disabled and Production HOLD.
