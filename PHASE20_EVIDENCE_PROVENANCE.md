# Phase 20 — Evidence Provenance & Reproducibility

## Objective
Make important NEMA-AGORA evidence traceable and reproducible without claiming environmental truth.

## Provenance unit
Each record binds:
- event type and event ID;
- authenticated actor;
- timestamp;
- dataset version and SHA-256 dataset hash;
- model identity where applicable;
- parent provenance IDs;
- SHA-256 evidence fingerprint;
- metadata;
- policy version.

## Chain
Evaluation → Annotation → Comparison → Admission → Controlled Shadow → Monitoring → Human Review → Lifecycle Decision.

A parent reference must resolve within the evidence set when a chain is verified.

## Reproducibility boundary
A provenance record is evidence metadata, not a copy of confidential input data. Hashes are used for integrity/fingerprinting and do not make sensitive data safe to disclose.

## Safety
Provenance does not establish environmental truth, regulatory status, enforcement priority, emergency response authority, NEMA authorization, or production approval.
