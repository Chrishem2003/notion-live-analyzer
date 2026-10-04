# Phase 91 — API Audit Lifecycle & Retention Governance

Defines a deterministic lifecycle evaluation for reconciled API audit evidence.

A recorded event can only enter retention evaluation after successful reconciliation. The evaluator returns RETAINED while within the configured retention window and EXPIRED after the window, based on an explicit evaluation timestamp.

Expiration is a lifecycle state, not deletion. The append-only historical registry remains authoritative for historical evidence. This phase does not establish environmental truth, regulatory status, enforcement authority, or NEMA authorization.
