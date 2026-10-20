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
- Each selected Sample must already relate to the chosen Project and Protocol and be classified `Demo` or `Synthetic/Test`.
- Each selected Experimental Data record must already relate to the same Project and Protocol, link to at least one Sample selected for the run, and be classified `Demo` or `Synthetic/Test`. Data records cannot be submitted without at least one selected Sample.
- Each supplied Source Evidence page must belong to the private Literature source and be classified `Demo` or `Synthetic/Test`.
- The selected dataset version and source-evidence page IDs are stored on the run and included in its deterministic manifest fingerprint. The API recomputes the SHA-256 manifest from submitted inputs and rejects a client-supplied mismatch; the UI does not accept a manually entered hash.

Invalid or incomplete relationships return HTTP 422 before the Analysis Runs record is created. This is intentional: the current three Demo samples have missing Project and Protocol links, so they must be mapped by a human before they can be used as run inputs. Do not bypass the gate or infer the intended mapping from names.

## Deployment inventory and separate API service

The Render blueprint now declares a separate `notion-live-analyzer-api` service, health-checks it at `/api/v1/health`, and starts it through `scripts/start_research_run_api.sh`. That startup script runs the read-only schema/relation preflight before starting Uvicorn; a mismatch or missing source ID stops the API from starting. The Streamlit service points to `https://notion-live-analyzer-api.onrender.com` by default. Confirm the actual Render service hostname after Blueprint sync.

**The free-tier blueprint is synthetic staging only.** It opts into an ephemeral SQLite ledger under `/tmp` because free service disks are not persistent. Never use this deployment for real research, regulated data, or production-grade idempotency. Before any real-research workflow, use an appropriate plan with persistent storage mounted at `/var/data`, set `RESEARCH_RUN_IDEMPOTENCY_DB=/var/data/research_run_idempotency.sqlite3`, and set `RESEARCH_RUN_ALLOW_EPHEMERAL_LEDGER=false`. Do not create paid resources without reviewing their cost.

Set `PLATFORM_API_KEY` to the same high-entropy value on both the Streamlit and API services. Set `NOTION_TOKEN` and all nine private data-source IDs only in the API service's Render dashboard. These values are marked `sync: false` in the Blueprint and are intentionally absent from Git. The API integration token should have access only to the required private sources.

The API endpoint is protected by `X-API-Key`; keep the key server-side. Do not expose it in browser code or paste it into Streamlit inputs.

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
