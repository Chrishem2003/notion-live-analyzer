"""Static safety checks for the proposed indicator ledger migration."""
from pathlib import Path


def _migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "supabase"
        / "004_nema_indicator_measurements.sql"
    )
    return path.read_text(encoding="utf-8").lower()


def test_indicator_ledger_enables_rls_and_denies_client_roles():
    sql = _migration()
    assert "alter table public.nema_indicator_measurements enable row level security" in sql
    assert "revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role" in sql


def test_indicator_ledger_service_role_is_read_only():
    sql = _migration()
    assert "grant select on table public.nema_indicator_measurements to service_role" in sql
    assert "grant insert on table public.nema_indicator_measurements to service_role" not in sql
    assert "grant update on table public.nema_indicator_measurements to service_role" not in sql
    assert "grant delete on table public.nema_indicator_measurements to service_role" not in sql


def test_verified_measurements_require_evidence_and_review_metadata():
    sql = _migration()
    for fragment in (
        "status <> 'verified'",
        "jsonb_array_length(source_refs) > 0",
        "jsonb_array_length(evidence_refs) > 0",
        "reviewer_id is not null",
        "verified_at is not null",
    ):
        assert fragment in sql


def test_missing_values_are_allowed_but_negative_values_are_not():
    sql = _migration()
    assert "value is null or value >= 0" in sql
    assert "numerator is null or numerator >= 0" in sql
    assert "denominator is null or denominator >= 0" in sql
