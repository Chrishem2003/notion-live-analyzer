from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations" / "supabase"


def test_owner_integrity_migration_prevents_reassignment_without_enabling_writes():
    sql = (MIGRATIONS / "003_nema_case_owner_integrity.sql").read_text(encoding="utf-8").lower()

    assert "before update of owner_id on public.nema_cases" in sql
    assert "old.owner_id is not null" in sql
    assert "new.owner_id is distinct from old.owner_id" in sql
    assert "raise exception 'nema case ownership cannot be reassigned'" in sql
    assert "does not grant" in sql
    assert "do not enable direct table writes" in sql


def test_owner_migration_order_is_explicit():
    owner_scope = MIGRATIONS / "002_nema_case_owner_scope.sql"
    owner_integrity = MIGRATIONS / "003_nema_case_owner_integrity.sql"

    assert owner_scope.is_file()
    assert owner_integrity.is_file()
    assert "after 002_nema_case_owner_scope.sql" in owner_integrity.read_text(encoding="utf-8")
