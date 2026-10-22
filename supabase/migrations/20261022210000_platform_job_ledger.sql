-- Durable, database-enforced job ledger for the unified platform.
-- Apply only through reviewed Supabase migrations. No production writes are enabled
-- by adding this file to GitHub; deployment and runtime configuration are separate gates.

create table if not exists public.platform_jobs (
    job_id uuid primary key default gen_random_uuid(),
    job_type text not null check (length(job_type) between 1 and 120),
    actor_scope text not null check (length(actor_scope) between 1 and 200),
    idempotency_key text not null check (length(idempotency_key) between 1 and 200),
    request_hash text not null check (request_hash ~ '^[0-9a-f]{64}$'),
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    status text not null default 'queued'
        check (status in ('queued', 'running', 'succeeded', 'failed', 'needs_review')),
    attempt_count integer not null default 0 check (attempt_count >= 0),
    max_attempts integer not null default 3 check (max_attempts between 1 and 10),
    worker_id text,
    lease_token uuid,
    lease_until timestamptz,
    result_json jsonb,
    error_json jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    started_at timestamptz,
    finished_at timestamptz,
    unique (actor_scope, idempotency_key)
);

create index if not exists platform_jobs_claim_idx
    on public.platform_jobs (status, lease_until, created_at);

create table if not exists public.platform_job_attempts (
    attempt_id bigint generated always as identity primary key,
    job_id uuid not null references public.platform_jobs(job_id) on delete restrict,
    attempt_number integer not null check (attempt_number > 0),
    worker_id text not null,
    lease_token uuid not null,
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    outcome text check (outcome in ('succeeded', 'failed', 'needs_review', 'lease_expired')),
    error_json jsonb,
    unique (job_id, attempt_number)
);

create table if not exists public.platform_audit_events (
    audit_id bigint generated always as identity primary key,
    job_id uuid references public.platform_jobs(job_id) on delete restrict,
    actor_scope text not null,
    event_type text not null check (length(event_type) between 1 and 120),
    event_json jsonb not null default '{}'::jsonb check (jsonb_typeof(event_json) = 'object'),
    created_at timestamptz not null default now()
);

create index if not exists platform_audit_job_idx
    on public.platform_audit_events (job_id, created_at, audit_id);

alter table public.platform_jobs enable row level security;
alter table public.platform_job_attempts enable row level security;
alter table public.platform_audit_events enable row level security;

revoke all on public.platform_jobs, public.platform_job_attempts, public.platform_audit_events
    from public, anon, authenticated;
grant select, insert, update on public.platform_jobs to service_role;
grant select, insert, update on public.platform_job_attempts to service_role;
grant select, insert on public.platform_audit_events to service_role;
grant usage, select on all sequences in schema public to service_role;

-- The audit table is append-only for ordinary SQL roles. The application writes
-- audit events in the same transaction as each state transition.
create or replace function public.platform_prevent_audit_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog, public
as $$
begin
    raise exception 'platform audit events are append-only';
end;
$$;

drop trigger if exists platform_audit_no_mutation on public.platform_audit_events;
create trigger platform_audit_no_mutation
before update or delete on public.platform_audit_events
for each row execute function public.platform_prevent_audit_mutation();

create or replace function public.platform_enqueue_job(
    p_job_type text,
    p_actor_scope text,
    p_idempotency_key text,
    p_request_hash text,
    p_payload jsonb,
    p_max_attempts integer default 3
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
    v_job public.platform_jobs%rowtype;
    v_inserted boolean := false;
begin
    if p_job_type is null or length(p_job_type) not between 1 and 120
       or p_actor_scope is null or length(p_actor_scope) not between 1 and 200
       or p_idempotency_key is null or length(p_idempotency_key) not between 1 and 200
       or p_request_hash is null or p_request_hash !~ '^[0-9a-f]{64}$'
       or p_payload is null or jsonb_typeof(p_payload) <> 'object'
       or p_max_attempts not between 1 and 10 then
        raise exception 'invalid job request' using errcode = '22023';
    end if;

    insert into public.platform_jobs (
        job_type, actor_scope, idempotency_key, request_hash, payload, max_attempts
    ) values (
        p_job_type, p_actor_scope, p_idempotency_key, p_request_hash, p_payload, p_max_attempts
    )
    on conflict (actor_scope, idempotency_key) do nothing
    returning * into v_job;

    if found then
        v_inserted := true;
    else
        select * into v_job
        from public.platform_jobs
        where actor_scope = p_actor_scope and idempotency_key = p_idempotency_key
        for update;

        if v_job.request_hash <> p_request_hash then
            raise exception 'idempotency key reused with a different request'
                using errcode = '22023';
        end if;
    end if;

    if v_inserted then
        insert into public.platform_audit_events (job_id, actor_scope, event_type, event_json)
        values (v_job.job_id, p_actor_scope, 'job.queued',
                jsonb_build_object('job_type', p_job_type, 'request_hash', p_request_hash));
    end if;

    return jsonb_build_object(
        'job_id', v_job.job_id,
        'status', v_job.status,
        'created', v_inserted,
        'attempt_count', v_job.attempt_count
    );
end;
$$;

create or replace function public.platform_claim_job(
    p_worker_id text,
    p_lease_seconds integer default 120
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
    v_job public.platform_jobs%rowtype;
    v_token uuid;
begin
    if p_worker_id is null or length(p_worker_id) not between 1 and 200
       or p_lease_seconds not between 10 and 1800 then
        raise exception 'invalid worker lease request' using errcode = '22023';
    end if;

    select * into v_job
    from public.platform_jobs
    where (
        status = 'queued'
        or (status = 'running' and lease_until < now() and attempt_count < max_attempts)
    )
    and attempt_count < max_attempts
    order by created_at, job_id
    for update skip locked
    limit 1;

    if not found then
        return null;
    end if;

    if v_job.status = 'running' then
        update public.platform_job_attempts
        set finished_at = now(), outcome = 'lease_expired',
            error_json = jsonb_build_object('reason', 'worker lease expired')
        where job_id = v_job.job_id and attempt_number = v_job.attempt_count
          and finished_at is null;
        insert into public.platform_audit_events (job_id, actor_scope, event_type, event_json)
        values (v_job.job_id, v_job.actor_scope, 'job.lease_expired',
                jsonb_build_object('previous_worker_id', v_job.worker_id));
    end if;

    v_token := gen_random_uuid();
    update public.platform_jobs
    set status = 'running',
        attempt_count = attempt_count + 1,
        worker_id = p_worker_id,
        lease_token = v_token,
        lease_until = now() + make_interval(secs => p_lease_seconds),
        started_at = coalesce(started_at, now()),
        updated_at = now()
    where job_id = v_job.job_id
    returning * into v_job;

    insert into public.platform_job_attempts (job_id, attempt_number, worker_id, lease_token)
    values (v_job.job_id, v_job.attempt_count, p_worker_id, v_token);

    insert into public.platform_audit_events (job_id, actor_scope, event_type, event_json)
    values (v_job.job_id, v_job.actor_scope, 'job.claimed',
            jsonb_build_object('worker_id', p_worker_id, 'attempt', v_job.attempt_count));

    return jsonb_build_object(
        'job_id', v_job.job_id, 'job_type', v_job.job_type, 'payload', v_job.payload,
        'attempt_count', v_job.attempt_count, 'max_attempts', v_job.max_attempts,
        'lease_token', v_token, 'lease_until', v_job.lease_until
    );
end;
$$;

create or replace function public.platform_finish_job(
    p_job_id uuid,
    p_worker_id text,
    p_lease_token uuid,
    p_status text,
    p_result jsonb default null,
    p_error jsonb default null
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
    v_job public.platform_jobs%rowtype;
begin
    if p_status not in ('succeeded', 'failed', 'needs_review') then
        raise exception 'invalid terminal status' using errcode = '22023';
    end if;
    if p_result is not null and jsonb_typeof(p_result) <> 'object' then
        raise exception 'result must be a JSON object' using errcode = '22023';
    end if;
    if p_error is not null and jsonb_typeof(p_error) <> 'object' then
        raise exception 'error must be a JSON object' using errcode = '22023';
    end if;

    update public.platform_jobs
    set status = p_status,
        result_json = p_result,
        error_json = p_error,
        updated_at = now(),
        finished_at = now(),
        lease_until = null
    where job_id = p_job_id
      and status = 'running'
      and worker_id = p_worker_id
      and lease_token = p_lease_token
    returning * into v_job;

    if not found then
        raise exception 'job lease is stale or not owned by this worker'
            using errcode = '42501';
    end if;

    update public.platform_job_attempts
    set finished_at = now(), outcome = p_status, error_json = p_error
    where job_id = v_job.job_id and attempt_number = v_job.attempt_count
      and worker_id = p_worker_id and lease_token = p_lease_token
      and finished_at is null;

    insert into public.platform_audit_events (job_id, actor_scope, event_type, event_json)
    values (v_job.job_id, v_job.actor_scope, 'job.' || p_status,
            jsonb_build_object('attempt', v_job.attempt_count, 'worker_id', p_worker_id));

    return jsonb_build_object('job_id', v_job.job_id, 'status', v_job.status);
end;
$$;

-- RPC-only interface: callers cannot directly mutate ledger tables through PostgREST.
revoke all on function public.platform_enqueue_job(text, text, text, text, jsonb, integer) from public, anon, authenticated;
revoke all on function public.platform_claim_job(text, integer) from public, anon, authenticated;
revoke all on function public.platform_finish_job(uuid, text, uuid, text, jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.platform_enqueue_job(text, text, text, text, jsonb, integer) to service_role;
grant execute on function public.platform_claim_job(text, integer) to service_role;
grant execute on function public.platform_finish_job(uuid, text, uuid, text, jsonb, jsonb) to service_role;
