# Phase 25 — Deployment & Reproducibility

NEMA-AGORA Phase 25 adds a non-secret deployment manifest for reproducible engineering and research evidence.

## Captured identity

- application identity
- Git revision
- Python/runtime identity
- platform identity
- policy versions
- dataset version/hash bindings already present in provenance
- configuration fingerprint
- dependency fingerprint
- manifest fingerprint

## Security boundary

The manifest must not contain secret values, personal data, confidential incident data, or credentials. It identifies a deployment; it does not prove environmental truth, environmental impact, NEMA authorization, regulatory status, or production suitability.

## Verification

A valid manifest requires a Git revision and required identity fields. Its fingerprint can be used to compare two deployment descriptions without exposing the underlying configuration.

The Phase 25 page requires persistent authenticated mode and the `intelligence:reproducibility` permission.

## Next hardening

Populate the Git revision automatically from the deployment environment and publish the manifest as a CI artifact, while keeping secrets excluded and human governance boundaries intact.
