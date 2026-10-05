# NEMA-AGORA Autonomous Build Changelog

## 2026-10-05
- Reconciled the durable build state with the product track.
- Phase 168: added governed operational case metrics.
- Phase 169: added deterministic pilot acceptance and safety-boundary gates.
- Phase 170: completed final architecture and acceptance checkpoint.
- Evaluation integrity was hardened: accuracy is recomputed from cases, incomplete model identity is rejected, and evaluation artifacts receive deterministic fingerprints.
- GitHub Actions for the then-current heads were not observed, so CI was never inferred as green.

## Release hardening: append-only transition reconstruction
- The immutable evidence-case base row remains unchanged after creation.
- Human-review and export transitions are persisted as append-only events and are now replayed deterministically into the effective case state.
- Event records require an existing case, matching provenance fingerprint, supported transition type, safe export boundary, and valid state transition.
- Stored case JSON is parsed and revalidated before use; malformed/tampered persistence is rejected.
- Reviewer inspection now reads effective state from the transition history rather than stale base-row state.
- Export events use a distinct export timestamp and retain the human actor/role.
- This hardening does not submit externally, enforce regulations, dispatch emergencies, or claim environmental truth.

## Current verification boundary
- Release-hardening implementation commit: 99b02be493a13d6751f472984623b1275ed7a67f.
- Durable build-state checkpoint commit: bdb57cc18c645dd55eda152143c3835e734e699b.
- GitHub Actions must be observed for that exact head before any green/validated claim.
- PR #10 remains draft and unmerged.
