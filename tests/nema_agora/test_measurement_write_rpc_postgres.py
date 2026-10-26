from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")
from psycopg2.extras import Json

ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="isolated PostgreSQL DATABASE_URL is not configured")
_setup_lock = threading.Lock()
_setup_done = False


def connect():
    return psycopg2.connect(DATABASE_URL)


@pytest.fixture(scope="module", autouse=True)
def migrated_postgres():
    global _setup_done
    with _setup_lock:
        if _setup_done:
            return
        with connect() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("CREATE ROLE anon NOLOGIN")
                cur.execute("CREATE ROLE authenticated NOLOGIN")
                cur.execute("CREATE ROLE service_role NOLOGIN")
                cur.execute("CREATE SCHEMA extensions")
                cur.execute("CREATE EXTENSION pgcrypto WITH SCHEMA extensions")
                cur.execute((ROOT / "migrations/supabase/004_nema_indicator_measurements.sql").read_text(encoding="utf-8"))
                cur.execute((ROOT / "migrations/supabase/006_nema_indicator_measurement_write_rpc.sql").read_text(encoding="utf-8"))
        _setup_done = True


def record(value=12):
    return {
        "indicator_id": "community_reports",
        "definition_version": "1.0",
        "reporting_period_start": "2026-10-01",
        "reporting_period_end": "2026-10-26",
        "reporting_timezone": "Africa/Kampala",
        "status": "measured",
        "value": value,
        "unit": "count",
        "numerator": None,
        "denominator": None,
        "exclusions": [],
        "source_refs": ["field-log-001"],
        "evidence_refs": [{"reference": "evidence/field-log-001.txt", "sha256": "a" * 64}],
        "calculation_method": "field-count-v1",
        "reviewer_id": None,
        "verified_at": None,
        "caveats": [],
    }


def call_rpc(measurement_id, key, payload, actor="integration-test-user", role="submitter"):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT public.submit_nema_indicator_measurement(%s, %s, %s, %s, %s)",
                (measurement_id, key, actor, role, Json(payload)),
            )
            result = cur.fetchone()[0]
        conn.commit()
        return result


def scalar(sql, args=()):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchone()[0]


def test_postgres_new_submission_and_identical_retry_are_atomic(migrated_postgres):
    measurement_id = "pg-new-" + uuid.uuid4().hex
    key = "pg-key-" + uuid.uuid4().hex
    first = call_rpc(measurement_id, key, record())
    replay = call_rpc(measurement_id, key, record())
    assert first["decision"] == "new"
    assert replay["decision"] == "replay"
    assert first["payload_sha256"] == replay["payload_sha256"]
    assert scalar("SELECT count(*) FROM public.nema_indicator_measurements WHERE measurement_id=%s", (measurement_id,)) == 1
    assert scalar("SELECT count(*) FROM public.nema_measurement_idempotency WHERE idempotency_key=%s", (key,)) == 1
    assert scalar("SELECT count(*) FROM public.nema_measurement_audit WHERE measurement_id=%s", (measurement_id,)) == 1


def test_postgres_rejects_changed_payload_for_same_idempotency_key(migrated_postgres):
    measurement_id = "pg-conflict-" + uuid.uuid4().hex
    key = "pg-key-" + uuid.uuid4().hex
    call_rpc(measurement_id, key, record(12))
    with pytest.raises(psycopg2.Error, match="idempotency key reused with a different payload"):
        call_rpc(measurement_id, key, record(13))
    assert scalar("SELECT count(*) FROM public.nema_measurement_audit WHERE measurement_id=%s", (measurement_id,)) == 1


def test_postgres_rolls_back_measurement_and_idempotency_if_audit_insert_fails(migrated_postgres):
    measurement_id = "pg-rollback-" + uuid.uuid4().hex
    key = "pg-key-" + uuid.uuid4().hex
    with connect() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("""
                CREATE OR REPLACE FUNCTION public.test_fail_nema_audit_insert()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'injected audit failure'; END;
                $$
            """)
            cur.execute("""
                CREATE TRIGGER test_fail_nema_audit_insert
                BEFORE INSERT ON public.nema_measurement_audit
                FOR EACH ROW EXECUTE FUNCTION public.test_fail_nema_audit_insert()
            """)
    try:
        with pytest.raises(psycopg2.Error, match="injected audit failure"):
            call_rpc(measurement_id, key, record())
    finally:
        with connect() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("DROP TRIGGER IF EXISTS test_fail_nema_audit_insert ON public.nema_measurement_audit")
                cur.execute("DROP FUNCTION IF EXISTS public.test_fail_nema_audit_insert()")
    assert scalar("SELECT count(*) FROM public.nema_indicator_measurements WHERE measurement_id=%s", (measurement_id,)) == 0
    assert scalar("SELECT count(*) FROM public.nema_measurement_idempotency WHERE idempotency_key=%s", (key,)) == 0
    assert scalar("SELECT count(*) FROM public.nema_measurement_audit WHERE measurement_id=%s", (measurement_id,)) == 0


def test_postgres_parallel_same_key_submissions_create_one_measurement(migrated_postgres):
    measurement_id = "pg-parallel-" + uuid.uuid4().hex
    key = "pg-key-" + uuid.uuid4().hex
    barrier = threading.Barrier(2)

    def submit():
        barrier.wait(timeout=10)
        return call_rpc(measurement_id, key, record())

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit(), range(2)))
    assert sorted(item["decision"] for item in results) == ["new", "replay"]
    assert scalar("SELECT count(*) FROM public.nema_indicator_measurements WHERE measurement_id=%s", (measurement_id,)) == 1
    assert scalar("SELECT count(*) FROM public.nema_measurement_audit WHERE measurement_id=%s", (measurement_id,)) == 1


def test_postgres_rejects_null_role_and_denies_client_execution(migrated_postgres):
    measurement_id = "pg-auth-" + uuid.uuid4().hex
    key = "pg-key-" + uuid.uuid4().hex
    with pytest.raises(psycopg2.Error, match="actor role is not allowed"):
        call_rpc(measurement_id, key, record(), role=None)
    assert scalar("SELECT has_function_privilege('anon', 'public.submit_nema_indicator_measurement(text,text,text,text,jsonb)', 'EXECUTE')") is False
    assert scalar("SELECT has_function_privilege('authenticated', 'public.submit_nema_indicator_measurement(text,text,text,text,jsonb)', 'EXECUTE')") is False
    assert scalar("SELECT has_function_privilege('service_role', 'public.submit_nema_indicator_measurement(text,text,text,text,jsonb)', 'EXECUTE')") is True


def test_postgres_audit_is_append_only(migrated_postgres):
    measurement_id = "pg-audit-" + uuid.uuid4().hex
    key = "pg-key-" + uuid.uuid4().hex
    call_rpc(measurement_id, key, record())
    with pytest.raises(psycopg2.Error, match="append-only"):
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE public.nema_measurement_audit SET actor_role='admin' WHERE measurement_id=%s", (measurement_id,))
                conn.commit()
