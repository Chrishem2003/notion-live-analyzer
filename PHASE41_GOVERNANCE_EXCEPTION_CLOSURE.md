# NEMA-AGORA Phase 41 — Governance Exception Closure

## Purpose

Phase 41 closes the loop between Phase 39 reconciliation and Phase 40 human resolution without rewriting historical evidence.

## Closure rules

An exception is CLOSED only when:

1. the current reconciliation identifies the exception;
2. a Phase 40 resolution matches the exact exception code, decision kind, artifact ID and current reconciliation fingerprint;
3. the resolution outcome is one of CORRECTED_AT_SOURCE, DUPLICATE_CONFIRMED, or FALSE_POSITIVE;
4. closure evidence supplies a stable non-identifying evidence_id and a valid SHA-256 evidence_hash.

ACKNOWLEDGED is a human acknowledgement, not closure. ESCALATED remains CONTROL_REQUIRED.

Missing evidence produces REVIEW_REQUIRED; stale resolution events never close a newer reconciliation.

## Safety and integrity

The closure evaluator is derived/read-only. It never edits authoritative source decisions, deletes or rewrites audit events, or silently repairs reconciliation gaps. Evidence references identify independently preserved evidence; the underlying evidence content is not ingested into the audit layer.

A CLOSED result is an engineering/research governance state only. It is not environmental truth, NEMA authorization, regulatory approval, enforcement authority, emergency response authority, or production approval.

## Product surface

pages/49_NEMA_AGORA_GOVERNANCE_EXCEPTION_CLOSURE.py provides an authenticated read-only closure review surface. Reviewers can inspect open exceptions, matching resolutions and explicit evidence requirements; the page does not mutate source records.

## Verification

Focused tests cover unresolved exceptions, missing evidence, valid hashed evidence, acknowledgement/escalation semantics, and stale-resolution rejection.
