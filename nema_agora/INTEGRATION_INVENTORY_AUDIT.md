# NEMA-AGORA Integration Inventory Audit

**Candidate:** integration PR #52  
**Branch:** `integration/nema-agora-current-main`  
**Review status:** first-pass static inventory triage; not a completed line-by-line code review  
**Release decision:** keep draft; do not merge or deploy solely on CI evidence

## What the integration currently contains

The PR reports 367 changed paths: the NEMA Streamlit page, the `nema_agora/` Python package, focused tests, and release/build-state documentation. The changed-file inventory includes approximately 180 package Python files and 182 NEMA-specific test files. CI on commit `10db722ea1837d481b43bdd2b9a8c6735ca35f26` passed the focused NEMA tests, compile/smoke checks, the repository suite, API container build, and API runtime import check.

These results establish that the checked workflows passed on that commit. They do not establish that every module is reachable, required, secure for production, or integrated with live external data.

## First-pass findings

### 1. The user-facing entrypoint has a clear primary path

- `pages/18_NEMA_AGORA.py` is the integrated Streamlit page.
- It delegates identity mapping to `nema_agora.auth.resolve_principal`, permission checks to `nema_agora.access`, workflow operations to `nema_agora.service`, and persistence to `nema_agora.storage`.
- Persistent mode requires explicit configuration and a provisioned server-side OIDC issuer/subject role binding. Missing/unauthorised identity stops access; invalid mode fails visibly; storage failure does not silently fall back to demo mode.
- Demo mode is session-only. It must not be presented as durable storage or evidence of deployment acceptance.

### 2. Security controls have useful automated coverage, but still need deployment verification

Existing focused tests cover server-side role binding, ignoring privilege claims supplied by the identity provider, fail-closed identity adapter errors, invalid storage mode, and an end-to-end synthetic record/review/audit/backup/restore journey.

Remaining risk: those are repository-level tests. They do not verify the deployed OIDC callback, real configured role bindings, filesystem permissions, Render persistence semantics, or direct access through any separately deployed API. Do not enable persistent mode until those are verified in the actual target environment.

### 3. The phase-numbered inventory is a maintenance risk

There are 50 changed Python filenames with a `phase<number>.py` suffix across implementation/test paths, including a cluster of governance-drift, recovery, authorization, retention, registry, decision-history, reconciliation, and lifecycle names numbered around phases 134–159. This naming pattern suggests a long incremental implementation history and overlapping concepts, but filenames alone do not prove duplication or that a module is unused.

**Do not mass-delete or rename these files yet.** First build an import/reference graph, identify public entrypoints and dynamically imported modules, map each test to its production module, and classify files as:
- active entrypoint/dependency;
- supported but not currently reached from the Streamlit page;
- test-only fixture/contract;
- probable duplicate or superseded implementation;
- unresolved pending owner review.

A module not imported by the Streamlit page may still be used by an API route, CLI, test, plugin, or deployment workflow. Static import absence is not enough to delete it.

### 4. Spatial/environmental integrations are not the same as live data access

The page imports spatial change, spatial quality, candidate detection, and evidence-bundle modules. The repository also includes Sentinel-2/Google Earth Engine-related modules. The current CI checks do not prove credentials, external APIs, actual imagery acquisition, coordinate reference handling, or environmental classifications against validated field observations. These capabilities must remain labelled as configured/experimental until an authenticated live-source test and independent validation exist.

## Next engineering sequence

1. Generate a machine-readable import/reference inventory for the package, including imports from the Streamlit page, API entrypoints, tests, workflow files, and dynamic imports where identifiable.
2. Identify the phase-numbered governance/reconciliation family and compare its data contracts, imports, and public functions before proposing any consolidation.
3. Add focused regression tests for every consolidation candidate before moving or removing code.
4. Keep changes additive or isolated until CI proves the refactor preserves contracts.
5. Verify the deployed page in demo mode, then verify OIDC and role boundaries; only then test persistent write/read/audit/backup/restore in an approved environment.
6. Re-run exact-head CI after every source or tracker change. Production remains blocked until security, storage, accessibility, data-governance, and institutional review gates have evidence.

## Explicit non-claims

This audit does not claim a production security certification, live NEMA/ELMIS/SWIMS integration, official regulatory endorsement, successful hosted deployment, or approval to use real environmental incident data.
