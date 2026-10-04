# NEMA-AGORA Autonomous Build Protocol

## Purpose
This protocol defines the autonomous, evidence-first build loop for the NEMA-AGORA independent prototype.

## Operating loop
1. Inspect repository state and persisted build state.
2. Identify the next unblocked capability.
3. Implement the smallest coherent change.
4. Add focused tests and documentation.
5. Validate imports, contracts, governance controls, deterministic fingerprints, and regression-sensitive behavior.
6. Diagnose and correct validation failures.
7. Re-run validation after correction.
8. Record the checkpoint and advance.
9. At architecture checkpoints, stop repetitive phase generation when it no longer adds material value and move to the next product capability.

## Mandatory safety boundaries
- Independent student-led prototype; no implied NEMA endorsement or integration.
- No live official NEMA/ELMIS/SWIMS integration.
- No autonomous enforcement, regulatory conclusions, emergency dispatch, or official report submission.
- AI outputs remain advisory and human-reviewed.
- Governance decisions authorize records or workflow states only; they do not execute external actions.
- No fabricated environmental observations, boundaries, providers, or regulatory facts.
- Secrets and credentials must never be committed.

## Stop conditions
Pause for explicit human input only for destructive/irreversible actions, missing credentials, unavailable permissions, materially ambiguous architecture choices, or safety-sensitive scope changes.

## Continuation
The repository is durable project memory. A new session should read this protocol, build state, roadmap, and changelog before continuing.
