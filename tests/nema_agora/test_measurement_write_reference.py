import sqlite3
import pytest

from nema_agora.measurement_write_reference import (
    MeasurementWriteConflict, MeasurementWriteError, initialize_reference_ledger,
    submit_measurement_reference,
)


def setup():
    db = sqlite3.connect(":memory:")
    initialize_reference_ledger(db)
    return db


def payload(**overrides):
    row = {"indicator_id": "DASH-LATENCY-001", "definition_version": "1.0.0",
           "reporting_period_start": "2026-10-01", "reporting_period_end": "2026-10-31",
           "reporting_timezone": "Africa/Kampala", "status": "measured", "value": 1.42,
           "unit": "seconds", "source_refs": ["benchmark://run-01"], "evidence_refs": [],
           "exclusions": [], "calculation_method": "p95 across 100 requests"}
    row.update(overrides)
    return row


def submit(db, **kw):
    args = {"measurement_id": "m-1", "payload": payload(), "idempotency_key": "idem-1",
            "actor_id": "issuer|test-user", "actor_role": "submitter"}
    args.update(kw)
    return submit_measurement_reference(db, **args)


def counts(db):
    return tuple(db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                 for t in ("indicator_measurements", "measurement_idempotency", "measurement_audit"))


def test_new_write_creates_all_three_records():
    db = setup()
    assert submit(db)["decision"] == "new"
    assert counts(db) == (1, 1, 1)


def test_identical_retry_returns_original_without_duplicate_audit():
    db = setup()
    first = submit(db)
    replay = submit(db, measurement_id="different-id")
    assert replay["decision"] == "replay"
    assert replay["measurement_id"] == first["measurement_id"]
    assert replay["audit_created"] is False
    assert counts(db) == (1, 1, 1)


def test_reused_key_with_changed_payload_conflicts():
    db = setup()
    submit(db)
    with pytest.raises(MeasurementWriteConflict):
        submit(db, payload=payload(value=1.55))
    assert counts(db) == (1, 1, 1)


def test_failure_rolls_back_measurement_idempotency_and_audit():
    db = setup()
    with pytest.raises(RuntimeError, match="Injected failure"):
        submit(db, fail_after_measurement_insert=True)
    assert counts(db) == (0, 0, 0)


def test_submission_cannot_self_assert_verified_status():
    db = setup()
    with pytest.raises(MeasurementWriteError, match="verification is separate"):
        submit(db, payload=payload(status="verified", evidence_refs=["artifact://report"],
                                   reviewer_id="reviewer-1", verified_at="2026-10-26T10:00:00+03:00"))
    assert counts(db) == (0, 0, 0)


@pytest.mark.parametrize("role", ["reviewer", "anonymous", "admin-untrusted"])
def test_rejects_roles_not_allowed_to_submit(role):
    db = setup()
    with pytest.raises(MeasurementWriteError, match="not allowed"):
        submit(db, actor_role=role)
    assert counts(db) == (0, 0, 0)


def test_audit_is_append_only():
    db = setup()
    submit(db)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        db.execute("UPDATE measurement_audit SET action='changed'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        db.execute("DELETE FROM measurement_audit")
