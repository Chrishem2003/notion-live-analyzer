# Workflow Side-Effect Idempotency and Reconciliation

## Why this exists

The local workflow runtime can retry a failed handler. If a handler calls an external provider and then loses its process or times out before saving the result, the external action may already have happened. Retrying the handler blindly can create duplicate records, alerts, charges, or notifications.

`modules/workflow_effects.py` adds a durable SQLite effect journal with a stable effect key and explicit `pending`, `confirmed`, and `uncertain` states.

## Required handler pattern

1. Derive a stable effect key from the workflow/run and the logical action. Do not generate a fresh random key on each retry.
2. Call `execute_idempotent_effect` before any external side effect.
3. Pass the supplied key to the downstream provider's own idempotency-key facility whenever supported.
4. If the provider times out or returns an ambiguous error, treat the outcome as uncertain. Do not replay automatically.
5. Query the provider using a stable remote identifier or idempotency key. Use `journal.reconcile` only after a real provider lookup establishes whether the effect happened.
6. Store only the minimum response needed to reconcile. Do not put secrets, raw credentials, or sensitive research payloads in effect metadata.

Example shape (provider-specific API is intentionally illustrative):

```python
result = execute_idempotent_effect(
    journal,
    effect_key=f"{workflow_id}:{run_id}:publish-result:v1",
    workflow_id=workflow_id,
    run_id=run_id,
    effect_name="publish-result",
    request={"destination": "synthetic-test-destination", "record_digest": digest},
    perform=lambda key: provider.publish(
        payload,
        idempotency_key=key,  # provider must actually enforce this
    ),
)
```

## Important guarantees and limits

- A confirmed local result is returned on repeated calls without calling the provider again.
- Reusing a key with different workflow/run/action/request identity is rejected.
- A provider exception marks the effect uncertain, and a repeated attempt is blocked pending reconciliation.
- The journal alone cannot guarantee exactly-once remote execution. The remote provider must deduplicate the key, or an operator must reconcile the remote outcome.
- The journal uses SQLite and is intended as a local adapter. It is not a distributed lock service and does not make multiple hosts safe.
- A provider that ignores idempotency keys can still perform a duplicate if a crash happens after the remote action but before local confirmation.
- Production use requires staging evidence for provider-specific idempotency, read-after-write reconciliation, restart recovery, database backup/restore, and secret handling.

## Test coverage

`tests/test_workflow_effects.py` covers confirmed replay suppression, ambiguous failure blocking, key/request conflicts, confirmed reconciliation, and safe re-arming only after an explicit negative reconciliation.
