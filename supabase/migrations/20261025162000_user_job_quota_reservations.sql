-- Atomic per-user rolling-window quota reservations for user-facing AI jobs.
-- Apply only after review in staging; never grant direct client table access.
create table if not exists public.user_job_quota_reservations (
    reservation_id bigint generated always as identity primary key,
    tenant_id uuid not null,
    idempotency_key text not null check (length(idempotency_key) between 1 and 200),
    reserved_at timestamptz not null default now(),
    unique (tenant_id, idempotency_key)
);
create index if not exists user_job_quota_reservations_window_idx
    on public.user_job_quota_reservations (tenant_id, reserved_at desc);
alter table public.user_job_quota_reservations enable row level security;
revoke all on public.user_job_quota_reservations from public, anon, authenticated;
grant select, insert, update, delete on public.user_job_quota_reservations to service_role;
grant usage, select on sequence public.user_job_quota_reservations_reservation_id_seq to service_role;

create or replace function public.reserve_user_job_quota(
    p_tenant_id uuid,
    p_idempotency_key text,
    p_limit integer default 20,
    p_window_seconds integer default 3600
) returns boolean
language plpgsql security definer set search_path = '' as $$
declare
    recent_count integer;
begin
    if p_tenant_id is null then raise exception 'tenant id is required'; end if;
    if p_idempotency_key is null or length(p_idempotency_key) < 1 or length(p_idempotency_key) > 200 then
        raise exception 'valid idempotency key is required';
    end if;
    if p_limit < 1 or p_limit > 1000 or p_window_seconds < 60 or p_window_seconds > 86400 then
        raise exception 'quota configuration out of range';
    end if;

    -- Serialize quota checks for this account so concurrent requests cannot overspend.
    perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(p_tenant_id::text, 0));

    if exists (
        select 1 from public.user_job_quota_reservations r
        where r.tenant_id = p_tenant_id and r.idempotency_key = p_idempotency_key
    ) then
        return true; -- safe retry: does not consume a second reservation
    end if;

    select count(*)::integer into recent_count
    from public.user_job_quota_reservations r
    where r.tenant_id = p_tenant_id
      and r.reserved_at > now() - make_interval(secs => p_window_seconds);

    if recent_count >= p_limit then return false; end if;

    insert into public.user_job_quota_reservations(tenant_id, idempotency_key)
    values (p_tenant_id, p_idempotency_key)
    on conflict (tenant_id, idempotency_key) do nothing;
    return true;
end;
$$;
revoke all on function public.reserve_user_job_quota(uuid, text, integer, integer) from public, anon, authenticated;
grant execute on function public.reserve_user_job_quota(uuid, text, integer, integer) to service_role;
