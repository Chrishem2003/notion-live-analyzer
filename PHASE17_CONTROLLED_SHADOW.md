# Phase 17 — Controlled Shadow Operations

## Purpose

Phase 17 creates a governed operational lane for running an **already admitted** advisory model in isolated shadow mode.

A controlled-shadow run does not modify the observation, workflow status, regulatory state, or official reporting state. It exists only to collect evidence about model behaviour under human review.

## Admission boundary

Execution is allowed only when a persisted Phase 16 admission record has the exact decision:

`ADMITTED_FOR_CONTROLLED_SHADOW`

The concrete adapter must match the admitted candidate exactly on:

- provider
- model version
- adapter name

An adapter with a different identity is rejected before execution.

## Actor binding

The service requires an authenticated, provisioned NEMA-AGORA principal and the `intelligence:controlled_shadow` permission.

The recorded actor is derived from the authenticated principal, not from caller-supplied identity.

## Safety contract

Every governed run remains advisory and requires human review.

The execution path reuses the Phase 12 shadow runner, including safe failure behaviour and source-case binding. The controlled-shadow ledger records success or failure, latency, model identity, source case, actor and output/error evidence.

No external model provider is enabled by Phase 17.

## Ledger

Controlled executions are recorded in the `controlled_shadow_runs` SQLite ledger with:

- unique run ID
- admission ID
- source case ID
- authenticated actor
- provider/model/adapter identity
- status
- latency
- output or error
- timestamp
- mandatory human-review flag

The governed execution operation persists the ledger entry exactly once.

## UI boundary

The Phase 17 Streamlit page is intentionally monitoring-first. It shows admitted models and the controlled-shadow ledger but does not expose arbitrary model execution.

A future adapter registry must bind a concrete implementation to an admitted candidate before user-facing execution can be enabled.

## Verification

The focused NEMA-AGORA workflow must pass:

- focused unit tests
- pilot-module compilation
- Streamlit startup smoke test

The repository-wide legacy workflow may remain independently blocked by unrelated legacy test infrastructure; that failure must not be represented as NEMA-AGORA validation.

## Scope statement

Phase 17 does **not** mean NEMA approval, production approval, regulatory authorization, official reporting permission, enforcement authority, emergency response capability, or environmental truth.

It is a controlled, human-reviewed advisory shadow operation only.
