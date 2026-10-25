-- Durable service-to-service queue for bounded platform jobs.
-- RLS is enabled and no anon/authenticated policies are created. Server-side
-- service_role is required. Do not treat this queue as per-user auth.
create table if not exists public.platform_jobs (
    job_id uuid primary key default gen_random_uuid(),
    tenant_id text not null,
    requested_by text not null,
    job_type text not null check (job_type in ('intelligence.solve')),
    status text not null default 'queued' check (status in ('queued','running','succeeded','failed','cancelled')),
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    result_json jsonb check (result_json is null or jsonb_typeof(result_json) = 'object'),
    error_code text,
    attempt_count integer not null default 0 check (attempt_count >= 0),
    max_attempts integer not null default 3 check (max_attempts between 1 and 10),
    idempotency_key text not null,
    payload_hash text not null,
    available_at timestamptz not null default now(),
    lease_expires_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    completed_at timestamptz,
    unique (tenant_id, idempotency_key)
);
create index if not exists platform_jobs_queue_idx on public.platform_jobs (status, available_at, created_at);
create index if not exists platform_jobs_tenant_created_idx on public.platform_jobs (tenant_id, created_at desc);
create table if not exists public.platform_job_events (
    event_id bigint generated always as identity primary key,
    job_id uuid not null references public.platform_jobs(job_id) on delete cascade,
    event_type text not null check (length(event_type) between 1 and 80),
    event_json jsonb not null default '{}'::jsonb check (jsonb_typeof(event_json) = 'object'),
    created_at timestamptz not null default now()
);
create index if not exists platform_job_events_job_idx on public.platform_job_events (job_id, created_at, event_id);
alter table public.platform_jobs enable row level security;
alter table public.platform_job_events enable row level security;
revoke all on public.platform_jobs from anon, authenticated;
revoke all on public.platform_job_events from anon, authenticated;
grant select, insert, update, delete on public.platform_jobs to service_role;
grant select, insert, update, delete on public.platform_job_events to service_role;
grant usage, select on sequence public.platform_job_events_event_id_seq to service_role;
create or replace function public.claim_platform_job(p_lease_seconds integer default 120)
returns setof public.platform_jobs language plpgsql security definer set search_path = '' as $$
begin
 if p_lease_seconds < 30 or p_lease_seconds > 900 then raise exception 'lease duration must be between 30 and 900 seconds'; end if;
 return query with candidate as (
  select j.job_id from public.platform_jobs as j
  where ((j.status = 'queued' and j.available_at <= now()) or (j.status = 'running' and j.lease_expires_at < now() and j.attempt_count < j.max_attempts))
  order by j.available_at asc, j.created_at asc for update skip locked limit 1
 ) update public.platform_jobs as j set status='running', attempt_count=j.attempt_count+1,
  lease_expires_at=now()+make_interval(secs=>p_lease_seconds), updated_at=now(), error_code=null
 from candidate c where j.job_id=c.job_id returning j.*;
end; $$;
revoke all on function public.claim_platform_job(integer) from public, anon, authenticated;
grant execute on function public.claim_platform_job(integer) to service_role;
create or replace function public.finish_platform_job(p_job_id uuid, p_result jsonb)
returns boolean language plpgsql security definer set search_path = '' as $$
begin
 if p_result is null or jsonb_typeof(p_result) <> 'object' then raise exception 'result must be a JSON object'; end if;
 update public.platform_jobs set status='succeeded', result_json=p_result, error_code=null, lease_expires_at=null, completed_at=now(), updated_at=now()
 where job_id=p_job_id and status='running';
 if not found then return false; end if;
 insert into public.platform_job_events(job_id,event_type,event_json) values (p_job_id,'job_succeeded','{}'::jsonb);
 return true;
end; $$;
revoke all on function public.finish_platform_job(uuid,jsonb) from public, anon, authenticated;
grant execute on function public.finish_platform_job(uuid,jsonb) to service_role;
create or replace function public.fail_platform_job(p_job_id uuid, p_error_code text, p_retry_delay_seconds integer default 30)
returns boolean language plpgsql security definer set search_path = '' as $$
declare next_status text;
begin
 if p_retry_delay_seconds < 0 or p_retry_delay_seconds > 3600 then raise exception 'retry delay must be between 0 and 3600 seconds'; end if;
 update public.platform_jobs set status=case when attempt_count < max_attempts then 'queued' else 'failed' end,
  available_at=case when attempt_count < max_attempts then now()+make_interval(secs=>p_retry_delay_seconds) else available_at end,
  error_code=left(coalesce(nullif(p_error_code,''),'worker_error'),80), lease_expires_at=null,
  completed_at=case when attempt_count < max_attempts then null else now() end, updated_at=now()
 where job_id=p_job_id and status='running' returning status into next_status;
 if not found then return false; end if;
 insert into public.platform_job_events(job_id,event_type,event_json)
 values (p_job_id,case when next_status='queued' then 'job_retry_scheduled' else 'job_failed' end,
 jsonb_build_object('error_code',left(coalesce(nullif(p_error_code,''),'worker_error'),80)));
 return true;
end; $$;
revoke all on function public.fail_platform_job(uuid,text,integer) from public, anon, authenticated;
grant execute on function public.fail_platform_job(uuid,text,integer) to service_role;
