# Phase 125 — Retention Authorization Registry Integrity Monitoring

## Purpose
Phase 125 adds a read-only health monitor over the append-only Phase 124 retention-authorization registry.

It detects evidence-integrity conditions such as invalid snapshots, sequence gaps, predecessor breaks, duplicate identities, registry count mismatches, registry-policy mismatches, and execution-gate violations. It does not repair, delete, rewrite, execute, enforce, dispatch emergencies, or make environmental/regulatory conclusions.

## Governance
- Policy: `phase125-v1`
- Expected registry policy: `phase124-v1`
- `read_only=True`
- `human_governed=True`
- `automatic_repair_performed=False`
- `execution_gate_closed=True`
- `execution_permitted=False`
- `execution_performed=False`
- Environmental, regulatory, enforcement, and emergency-action fields remain `None`.

## States
- `NO_HISTORY` → `REVIEW_RETENTION_REGISTRY`
- `RETENTION_REGISTRY_HEALTHY` → `NO_RETENTION_REGISTRY_ACTION`
- `CONTROL_REQUIRED` → `PRESERVE_AND_ESCALATE`

## Flow
Phase 124 registry → Phase 125 monitor → human review/retention governance layer.

The monitor is evidence about registry integrity only. A healthy state is not proof of environmental compliance, and a control-required state does not authorize automated remediation.

## Validation
The monitor exposes `validate_retention_registry_monitor()`, including deterministic fingerprint validation and immutable governance/execution controls.

## Test coverage
Tests cover empty history, healthy deterministic monitoring, policy mismatch, count mismatch, sequence gaps, real Phase 124 registry reads, and tamper detection.
