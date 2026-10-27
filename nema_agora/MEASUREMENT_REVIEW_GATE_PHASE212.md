# Phase 212 — independent measurement review gate

Status: implemented as a framework-neutral, in-memory validation boundary; not connected to an HTTP route or persistence.

## Controls added

- Requires a trusted authenticated principal with reviewer, coordinator, or admin role.
- Requires the persisted submission actor so the submitter cannot review their own record.
- Allows only explicit decisions: accept_for_verification, request_correction, and reject.
- Requires a reason for correction or rejection and a timezone-aware ISO-8601 timestamp.
- Requires evidence references before a reviewer may recommend separate verification.
- An acceptance is only a recommendation. The event explicitly keeps the measurement status at measured, sets verification_performed to false, and does not claim evidence authenticity.
- The function performs no database writes. A future route must load the canonical record from storage, derive reviewer identity from verified auth, append an immutable audit event transactionally, and separately implement any verified-status transition with a distinct authorized action.

## Remaining gates

This module does not establish reviewer independence unless the caller supplies a trusted submission actor loaded from the database. It is not yet wired to the UI/API, and it does not prove the evidence bytes match the stored digest. Those checks must be enforced at the integration boundary. No live data or migration was changed.
