# Bio-Research Analysis Run Write-back

## Purpose

The Research Run write-back path links the Streamlit Research Analyzer to the private Bio-Research Enterprise workspace. It records a reproducibility entry in the private Analysis Runs register, with verified relations to project, protocol, samples and experimental-data records.

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
- RESEARCH_RUN_IDEMPOTENCY_DB: absolute path to a persistent SQLite file. All API workers must share the same file on storage that supports SQLite locking.

For the **full relation-graph preflight**, also configure these private source IDs in the API environment:
- NOTION_LITERATURE_DATA_SOURCE_ID: private Literature source.
- NOTION_GENOMIC_SEQUENCE_DATA_SOURCE_ID: private Genomic Sequence Log source.
- NOTION_TASKS_DATA_SOURCE_ID: private Daily Task source.
- NOTION_BRAIN_NOTES_DATA_SOURCE_ID: private Brain Notes source.

The API endpoint itself writes only to Analysis Runs and validates its project/protocol/sample/data relations. The extra four IDs let the preflight check the complete connected private graph, including project tasks, literature and genomic-sequence links.

Use the exact private source IDs shown by the Notion data-source schema. The currently audited private IDs are:

| Environment variable | Private data source UUID |
|---|---|
| `NOTION_ANALYSIS_RUNS_DATA_SOURCE_ID` | `eb1a60a3-e6e3-4f4d-bd50-0c63866ee937` |
| `NOTION_PROJECTS_DATA_SOURCE_ID` | `cf591428-06c6-83d1-b2bc-87f9d5d1a71f` |
| `NOTION_PROTOCOLS_DATA_SOURCE_ID` | `fa69173a-a184-486d-8730-4897eead8f34` |
| `NOTION_SAMPLES_DATA_SOURCE_ID` | `de491428-06c6-827b-9f90-87269d0a3e57` |
| `NOTION_EXPERIMENTAL_DATA_DATA_SOURCE_ID` | `e9391428-06c6-8361-95eb-0751507c9afd` |
| `NOTION_LITERATURE_DATA_SOURCE_ID` | `23791428-06c6-83ff-9eb1-079c65f7b2db` |
| `NOTION_GENOMIC_SEQUENCE_DATA_SOURCE_ID` | `e6491428-06c6-83a6-bcb6-87bd19bbe65a` |
| `NOTION_TASKS_DATA_SOURCE_ID` | `27f91428-06c6-82c9-8fe5-07e122070367` |
| `NOTION_BRAIN_NOTES_DATA_SOURCE_ID` | `8af91428-06c6-83a4-b0b7-074c0a6d17d4` |

These are identifiers, not credentials. The `35f91428-...` sources inspected in the published-template branch are template sources and must **not** be used for this live integration. Re-fetch the schema and verify the parent path before changing these values. The API validates each related page's parent source against the configured IDs.

Start the API in a trusted deployment:

    uvicorn api_server:app --host 0.0.0.0 --port 8000

Put the API behind HTTPS and network controls before exposing it outside a trusted environment. Do not use a per-container ephemeral SQLite path or multiple replicas with separate ledgers.

## Deployment inventory and separate API service

The repository's current Render blueprint declares the Streamlit web service and a keepalive cron job; it does not provision the research-run API service or persistent idempotency storage. The Dockerfile now declares a default Streamlit command so Docker-based web deployments have an explicit process. This does not deploy the API.

For Render, create a separate private/internal API service from this repository and override its Docker command to:

    uvicorn api_server:app --host 0.0.0.0 --port $PORT

Configure the required API environment variables listed above and attach persistent storage mounted at /var/data; set RESEARCH_RUN_IDEMPOTENCY_DB=/var/data/research_run_idempotency.sqlite3. If the chosen plan cannot provide persistent storage, do not treat the service as accepted for reliable multi-worker operation. Keep the API private to the Streamlit service where possible, or apply HTTPS, network access controls and secret management. Do not expose the API key in the browser or commit it.

The Streamlit deployment needs RESEARCH_RUN_API_URL set to the API's reachable HTTPS URL (or a private internal URL supported by the deployment) and the matching PLATFORM_API_KEY. No API service or disk is provisioned automatically by the current blueprint; deployment must be an explicit, reviewed step.

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

1. Confirm Notion integration access to the four private data sources.
2. Confirm the source IDs above point to private workspace data sources, not template sources.
3. Start the API with a persistent shared idempotency database.
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

The automated tests cover the adapter, ledger, API authentication/configuration, relation validation, client behavior, manifest fingerprinting and UI syntax. These tests use mocks and do not prove that the deployed service can authenticate to Notion. The feature branch must be merged and deployment configured before the live staging checklist can be run.
