-- NEMA-AGORA managed PostgreSQL foundation (read-only API phase).
-- Apply only to the intended Supabase project after confirming its project URL.
-- This migration intentionally grants the API service SELECT only. Do not grant
-- direct case/audit writes until authenticated actor identity, idempotency,
-- optimistic concurrency, and transactional audit RPCs are deployed and tested.

begin;

create table if not exists public.nema_cases (
    case_id text primary key,
    record_json jsonb not null,
    version integer not null default 1 check (version >= 1),
    created_at timestamptz not null,
    updated_at timestamptz not null,
    constraint nema_cases_record_object check (jsonb_typeof(record_json) = 'object')
);

create table if not exists public.nema_case_audit (
    audit_id text primary key,
    case_id text not null references public.nema_cases(case_id) on delete restrict,
    event_type text not null,
    event_json jsonb not null,
    created_at timestamptz not null,
    constraint nema_case_audit_event_object check (jsonb_typeof(event_json) = 'object')
);

create index if not exists idx_nema_case_audit_case_created
    on public.nema_case_audit (case_id, created_at, audit_id);

create or replace function public.reject_nema_case_audit_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'NEMA case audit events are append-only';
end;
$$;

drop trigger if exists nema_case_audit_no_update on public.nema_case_audit;
create trigger nema_case_audit_no_update
before update on public.nema_case_audit
for each row execute function public.reject_nema_case_audit_mutation();

drop trigger if exists nema_case_audit_no_delete on public.nema_case_audit;
create trigger nema_case_audit_no_delete
before delete on public.nema_case_audit
for each row execute function public.reject_nema_case_audit_mutation();

alter table public.nema_cases enable row level security;
alter table public.nema_case_audit enable row level security;

-- No client-facing anon/authenticated access. The API uses its server-side key.
revoke all on table public.nema_cases from anon, authenticated, service_role;
revoke all on table public.nema_case_audit from anon, authenticated, service_role;
grant usage on schema public to service_role;
grant select on table public.nema_cases to service_role;
grant select on table public.nema_case_audit to service_role;

commit;

-- After applying, verify table names/columns and role grants before configuring
-- the application. The application still reports storage_durability_verified=false
-- until provider configuration, backup/export, and restore testing are completed.
