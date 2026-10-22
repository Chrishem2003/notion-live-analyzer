# NEMA-AGORA Integration Inventory Audit

**Candidate:** integration PR #52  
**Branch:** `integration/nema-agora-current-main`  
**Review status:** static inventory executed; architecture integration gaps identified; no modules mass-deleted  
**Release decision:** keep draft; do not merge or deploy as a complete NEMA service yet

## Executed inventory

The report-only CI scan ran against the candidate and reported:

- 180 Python modules under `nema_agora/`.
- 425 Python files scanned across the package, Streamlit pages, and tests.
- 26 phase-suffixed package modules.
- 0 unresolved internal `nema_agora.*` imports in the scanned source.
- 82 modules with no detected runtime importers from other package modules or Streamlit pages.
- All 82 of those modules are referenced by tests, but are not imported into the current scanned runtime path.

This is an architecture/integration signal, **not a finding that 82 files are safe to delete**. Some modules are deliberately standalone API applications or future provider boundaries. The static scanner cannot establish whether another deployment, external caller, CLI, or dynamic import uses a module unless that entrypoint is inspected.

## Confirmed integration boundary

The current Streamlit entrypoint is `pages/18_NEMA_AGORA.py`. It uses the NEMA service layer for the implemented workspace journey.

The existing API container is not a NEMA spatial API deployment:

- `Dockerfile.api` starts `uvicorn api_server:app`.
- `api_server.py` does not import `nema_agora`; its current routes cover the CHRISHEM research-run, task, swarm/RAG, webhook, health, and chat-token surfaces.
- The NEMA package contains separate FastAPI modules such as `nema_agora.fastapi_authenticated_routes` and `nema_agora.fastapi_spatial_evidence_app`, but the current `api_server:app` does not mount them.

Therefore, passing the API container build does **not** mean the NEMA spatial-evidence API is deployed. The NEMA Streamlit page is integrated into the repository, while these separate NEMA API surfaces remain standalone contracts unless an approved entrypoint/service is explicitly wired and verified.

## First-pass findings

### 1. User-facing entrypoint

- `pages/18_NEMA_AGORA.py` is the integrated Streamlit page.
- It delegates identity mapping to `nema_agora.auth.resolve_principal`, permission checks to `nema_agora.access`, workflow operations to `nema_agora.service`, and persistence to `nema_agora.storage`.
- Persistent mode requires explicit configuration and a provisioned server-side OIDC issuer/subject role binding. Missing/unauthorised identity stops access; invalid mode fails visibly; storage failure does not silently fall back to demo mode.
- Demo mode is session-only and is not evidence of durable storage or deployment acceptance.

### 2. Security controls and deployment gap

Existing tests cover server-side role binding, ignoring privilege claims supplied by the identity provider, fail-closed identity adapter errors, invalid storage mode, synthetic record/review/audit, and backup/restore.

Those are repository-level checks. They do not verify deployed OIDC callbacks, actual role bindings, Render filesystem persistence, direct API authorization, or real external data ingestion. The current deployed API entrypoint is not the NEMA spatial API, so that integration must be designed explicitly before claiming the spatial API is live.

A route-level review found that the legacy standalone spatial API accepted a caller-provided database path and treated the presence of any Authorization header as authentication while accepting caller-supplied actor/role values. A query test even treated `Bearer demo` as sufficient. The two FastAPI query entrypoints have now been changed to fail closed with HTTP 503 until a trusted server-side identity verifier is wired; the database path is read from server configuration rather than request parameters. This is a containment fix, **not a completed authentication integration**. The query routes remain disabled, and their new exact-head CI must pass before this candidate is considered validated.

### 3. Test-only modules require product decisions

The 82 modules with no detected runtime importer include governance/audit/reconciliation helpers, separate FastAPI route/app modules, spatial evidence utilities, remote-sensing adapters, and reporting/recovery contracts. All have test references, but tests alone do not make a feature reachable by end users.

Classify each module before cleanup:
- active Streamlit dependency;
- intended standalone API/worker entrypoint, with a documented deployment target;
- supported library/helper invoked through a dynamic or external entrypoint;
- test-only contract or fixture;
- superseded/duplicate implementation, supported by dependency and contract evidence;
- unresolved pending owner review.

In particular, `nema_agora.gee_boundary` and the Phase 159 continuity/reconciliation module have dedicated contract tests now, but no detected runtime importer. Keep them until their intended integration is decided. The Earth Engine boundary is not a live provider connection; the module itself requires an injected adapter.

### 4. Phase-numbered governance family

The 26 phase-suffixed package files cluster around governance-drift, recovery, authorization, retention, registry, decision-history, continuity, review, and reconciliation concepts (roughly phases 134–159).

The naming suggests a long incremental implementation history and overlapping concepts, but filenames alone do not prove duplication. Before consolidation, trace each public function, data contract, static and dynamic importer, associated test, and intended API/worker entrypoint. Do not mass-delete or rename modules based on their names or the absence of a page import.

### 5. Environmental data claims

The page imports spatial change, spatial quality, candidate detection, and evidence-bundle modules. Sentinel-2/Google Earth Engine-related modules exist, but the CI checks do not prove credentials, external API access, actual imagery acquisition, coordinate-reference handling, or classification accuracy against validated field observations. Keep these capabilities labelled as configured/experimental until an authorized live-source test and independent validation exist.

## Feature-to-entrypoint map and API boundary decision

The first-pass module classification is now recorded in [`nema_agora/FEATURE_ENTRYPOINT_MAP.md`](FEATURE_ENTRYPOINT_MAP.md). It groups all 82 no-runtime-importer modules into provisional governance/audit API contracts, standalone API and spatial/provider boundaries, governance/evidence libraries, and review/operations/reporting/spatial-review modules. The categories are based on names and architecture signals and must be confirmed by contract-level review; they are not deletion decisions.

**Pilot boundary decision:** keep the current Streamlit NEMA page as the only integrated NEMA user entrypoint for now. Do not mount the NEMA FastAPI apps into the existing `api_server:app`, because that API currently uses a shared platform API key and does not import NEMA. NEMA's OIDC role-binding controls need an explicit, independently tested API authorization design. Keep spatial API endpoints unexposed until the route-level security and deployment target are approved. A separate authenticated service may be considered after the contracts and acceptance tests are complete.

## Next engineering sequence

1. Trace public functions/classes, dependencies, side effects, matching tests, authorization, persistence, and intended entrypoints for each module family in the map.
2. Compare the phase-numbered governance/reconciliation family by public contract and behavior; add equivalence/regression tests before consolidation. Do not mass-delete by filename.
3. For each retained user-facing feature, test the full path from UI/API entrypoint through permission check, service, persistence, audit, and tests.
4. Verify deployed Streamlit navigation and demo mode, then OIDC/role boundaries. Only then test persistent write/read/audit/backup/restore in an approved environment.
5. Re-run exact-head CI after source or tracker changes. Production remains blocked until security, storage, accessibility, data-governance, and institutional review gates have evidence.

## Explicit non-claims

This audit does not claim production security certification, live NEMA/ELMIS/SWIMS integration, official regulatory endorsement, successful hosted NEMA spatial API deployment, or approval to use real environmental incident data.
