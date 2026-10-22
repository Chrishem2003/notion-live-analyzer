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

## Next engineering sequence

1. Create a feature-to-entrypoint map for the 82 test-only modules; distinguish standalone APIs from modules intended for the Streamlit journey.
2. Decide whether NEMA spatial endpoints should be mounted into the existing API, deployed as a separate authenticated service, or remain explicitly unexposed for the pilot. Do not silently attach a second app to the current API.
3. For each retained user-facing feature, trace the path from UI/API entrypoint through authorization, service, persistence, audit, and tests.
4. Add regression tests before consolidation; keep changes additive until contracts and exact-head CI prove compatibility.
5. Verify deployed Streamlit navigation and demo mode, then OIDC/role boundaries. Only then test persistent write/read/audit/backup/restore in an approved environment.
6. Re-run exact-head CI after source or tracker changes. Production remains blocked until security, storage, accessibility, data-governance, and institutional review gates have evidence.

## Explicit non-claims

This audit does not claim production security certification, live NEMA/ELMIS/SWIMS integration, official regulatory endorsement, successful hosted NEMA spatial API deployment, or approval to use real environmental incident data.
