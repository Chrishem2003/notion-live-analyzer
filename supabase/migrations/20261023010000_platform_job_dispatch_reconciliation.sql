-- Reliable dispatch reconciliation for the durable platform job ledger.
-- This migration is safe to apply after 20261022210000_platform_job_ledger.sql.
-- It does not enable the feature flag or execute real-world job handlers.

alter table public.platform_jobs
    add column if not exists dispatch_requested_at timestamptz;

create index if not exists platform_jobs_dispatch_idx
    on public.platform_jobs (dispatch_requested_at, created_at)
    where status = 'queued' or status = 'running';

-- A claimed job no longer needs its previous dispatch reservation. This also
-- makes a handler-failure requeue eligible for prompt redispatch.
create or replace function public.platform_reset_dispatch_request()
returns trigger
language plpgsql
set search_path = pg_catalog, public
as $$
begin
    if new.status = 'running' and old.status is distinct from 'running' then
        new.dispatch_requested_at := null;
    end if;
    return new;
end;
$$;

drop trigger if exists platform_reset_dispatch_request_on_claim on public.platform_jobs;
create trigger platform_reset_dispatch_request_on_claim
before update of status on public.platform_jobs
for each row execute function public.platform_reset_dispatch_request();

-- Atomically reserve a bounded batch for broker dispatch. Repeated beat ticks
-- cannot flood the broker: an unclaimed reservation becomes eligible again
-- after 60 seconds. Expired running leases are included for crash recovery.
create or replace function public.platform_reserve_dispatches(
    p_limit integer default 25
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
    v_jobs jsonb;
begin
    if p_limit is null or p_limit not between 1 and 100 then
        raise exception 'dispatch batch limit must be between 1 and 100'
            using errcode = '22023';
    end if;

    with candidates as (
        select j.job_id
        from public.platform_jobs as j
        where (
            j.status = 'queued'
            or (j.status = 'running' and j.lease_until < now())
        )
          and (
            j.dispatch_requested_at is null
            or j.dispatch_requested_at <= now() - interval '60 seconds'
          )
        order by j.created_at, j.job_id
        for update skip locked
        limit p_limit
    ),
    reserved as (
        update public.platform_jobs as j
        set dispatch_requested_at = now()
        from candidates as c
        where j.job_id = c.job_id
        returning j.job_id
    )
    select coalesce(
        jsonb_agg(jsonb_build_object('job_id', job_id)),
        '[]'::jsonb
    )
    into v_jobs
    from reserved;

    return v_jobs;
end;
$$;

revoke all on function public.platform_reserve_dispatches(integer)
    from public, anon, authenticated;
grant execute on function public.platform_reserve_dispatches(integer)
    to service_role;
