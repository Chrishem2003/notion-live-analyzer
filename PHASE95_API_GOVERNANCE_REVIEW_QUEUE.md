# Phase 95 — API Governance Review Queue

Adds a persistent, append-only review queue for ready API governance casebooks.

Queue admission requires CASEBOOK_READY and a bounded human-review priority. Review IDs are deterministic and candidate cases cannot be silently duplicated. Ordering is deterministic by priority and review ID.

The queue is read-only until a future authorized human review workflow. It does not execute regulatory, environmental, enforcement, or emergency decisions.
