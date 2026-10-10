# Phase 173 — Integrated Pilot Verification

The automated test `tests/nema_agora/test_pilot_end_to_end.py` covers one synthetic journey across principal-bound observation creation, reviewer transition, audit-event attribution, SQLite backup, restore to a separate database, and post-restore record/history verification.

Validation requires the focused NEMA-AGORA workflow to pass unit tests, Python compilation, and Streamlit startup smoke checks on the exact candidate commit.

This is service/database integration evidence only. It does not replace browser-level acceptance, a production-like deployment rehearsal, identity-provider review, external backup validation, accessibility review, or institutional approval. Keep the execution gate closed until all release evidence is independently reviewed.
