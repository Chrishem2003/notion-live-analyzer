-- Shared AI distributed fixed-window rate limiting without an additional paid service.
-- REVIEW ONLY: do not apply until this migration and service-role handling are approved.
create schema if not exists private;

revoke all on schema private from public, anon, authenticated;

create table if not exists private.shared_ai_rate_limits (
    actor_hash text not null check (actor_hash ~ '^[0-9a-f]{64}$'),
    window_start timestamptz not null,
    request_count integer not null check (request_count >= 1),
    primary key (actor_hash, window_start)
);

revoke all on table private.shared_ai_rate_limits from public, anon, authenticated, service_role;

create or replace function public.consume_shared_ai_rate_limit(
    p_actor_hash text,
    p_limit integer
)
returns integer
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_window_start timestamptz := date_trunc('minute', now());
    v_count integer;
begin
    if p_actor_hash is null or p_actor_hash !~ '^[0-9a-f]{64}$' then
        raise exception 'invalid actor hash';
    end if;
    if p_limit is null or p_limit < 1 or p_limit > 120 then
        raise exception 'invalid rate limit';
    end if;

    insert into private.shared_ai_rate_limits(actor_hash, window_start, request_count)
    values (p_actor_hash, v_window_start, 1)
    on conflict (actor_hash, window_start)
    do update set request_count = private.shared_ai_rate_limits.request_count + 1
    returning request_count into v_count;

    -- Opportunistic cleanup on roughly 1% of requests, serialized by an
    -- advisory transaction lock. Quota enforcement never depends on cleanup.
    -- This avoids scanning the quota table on every request.
    if pg_catalog.random() < 0.01
       and pg_catalog.pg_try_advisory_xact_lock(2026102500::bigint) then
        delete from private.shared_ai_rate_limits
        where window_start < now() - interval '2 hours';
    end if;

    return v_count;
end;
$function$;

revoke all on function public.consume_shared_ai_rate_limit(text, integer) from public, anon, authenticated;
grant execute on function public.consume_shared_ai_rate_limit(text, integer) to service_role;
