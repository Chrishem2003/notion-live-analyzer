from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "migrations" / "supabase" / "006_nema_indicator_measurement_write_rpc.sql"


def test_write_rpc_is_explicitly_proposed_and_transactional():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "proposed; not applied" in sql
    assert sql.count("begin;") == 1
    assert sql.count("commit;") == 1
    assert "security definer" in sql
    assert "set search_path = pg_catalog" in sql
    assert "pg_advisory_xact_lock" in sql


def test_rpc_limits_execution_to_server_role():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "to service_role" in sql
    assert "from public, anon, authenticated, service_role" in sql
    assert "grant execute on function public.submit_nema_indicator_measurement" in sql


def test_measurement_idempotency_and_audit_are_constrained():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "idempotency_key text primary key" in sql
    assert "payload_sha256" in sql
    assert "measurement audit events are append-only" in sql
    assert "before update" in sql
    assert "before delete" in sql
    assert "pg_advisory_xact_lock" in sql
    assert "idempotency key reused with a different payload" in sql


def test_submission_does_not_allow_self_verification():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "p_record->>'status' is distinct from 'measured'" in sql
    assert "verification is a separate review action" in sql
    assert "does not authenticate p_actor_id/p_actor_role" in sql


def test_measurement_and_audit_writes_are_in_one_function_transaction():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "insert into public.nema_indicator_measurements" in sql
    assert "insert into public.nema_measurement_idempotency" in sql
    assert "insert into public.nema_measurement_audit" in sql
    assert sql.index("insert into public.nema_indicator_measurements") < sql.index("insert into public.nema_measurement_idempotency") < sql.index("insert into public.nema_measurement_audit")


def test_rpc_rejects_null_actor_role_and_missing_or_blank_required_fields():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "if p_actor_role is null or p_actor_role not in" in sql
    assert "p_record->>'definition_version' is null" in sql
    assert "length(pg_catalog.btrim(p_record->>'definition_version')) = 0" in sql
    assert "length(pg_catalog.btrim(p_record->>'reporting_timezone')) = 0" in sql
    assert "p_record->>'reporting_period_start' is null" in sql
    assert "p_record->>'reporting_period_end' is null" in sql


def test_rpc_normalizes_invalid_reporting_date_errors():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "reporting period dates must be valid iso dates" in sql
    assert "using errcode = '22023'" in sql


def test_rpc_computes_digest_from_record_in_database_not_caller_argument():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "v_payload_sha256 := " in sql
    assert "extensions.digest(" in sql
    assert "jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)" in sql
    assert "p_payload_sha256" not in sql
    assert "submit_nema_indicator_measurement(text, text, text, text, jsonb)" in sql



def test_rpc_owner_transfer_uses_temporary_schema_create_grant_only():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    grant = "grant create on schema public to nema_measurement_writer;"
    transfer = "owner to nema_measurement_writer;"
    revoke = "revoke create on schema public from nema_measurement_writer;"
    assert grant in sql
    assert transfer in sql
    assert revoke in sql
    assert sql.index(grant) < sql.index(transfer) < sql.index(revoke)



def test_evidence_artifact_provenance_is_transactional_and_restricted():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "create table if not exists public.nema_evidence_artifacts" in sql
    assert "alter table public.nema_evidence_artifacts enable row level security" in sql
    assert "revoke all on table public.nema_evidence_artifacts from anon, authenticated, service_role" in sql
    assert "grant insert on table public.nema_evidence_artifacts to nema_measurement_writer" in sql
    assert "grant select on table public.nema_evidence_artifacts to service_role" in sql
    assert "insert into public.nema_evidence_artifacts" in sql
    assert "object_key ~ '^sha256/[0-9a-f]{2}/[0-9a-f]{64}
    assert sql.index("insert into public.nema_indicator_measurements") < sql.index("insert into public.nema_evidence_artifacts") < sql.index("insert into public.nema_measurement_idempotency") < sql.index("insert into public.nema_measurement_audit")


def test_evidence_reference_must_be_content_addressed_and_match_digest():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "reference') !~ '^[a-z0-9][a-z0-9._-]{1,62}/sha256/[0-9a-f]{2}/[0-9a-f]{64}$'" in sql
    assert "split_part(evidence_ref.item->>'reference', '/', 3) <> substr" in sql
    assert "split_part(evidence_ref.item->>'reference', '/', 4) <> pg_catalog.lower" in sql
" in sql
    assert sql.index("insert into public.nema_indicator_measurements") < sql.index("insert into public.nema_evidence_artifacts") < sql.index("insert into public.nema_measurement_idempotency") < sql.index("insert into public.nema_measurement_audit")


def test_evidence_reference_must_be_content_addressed_and_match_digest():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "reference') !~ '^[a-z0-9][a-z0-9._-]{1,62}/sha256/[0-9a-f]{2}/[0-9a-f]{64}$'" in sql
    assert "split_part(evidence_ref.item->>'reference', '/', 3) <> substr" in sql
    assert "split_part(evidence_ref.item->>'reference', '/', 4) <> pg_catalog.lower" in sql
