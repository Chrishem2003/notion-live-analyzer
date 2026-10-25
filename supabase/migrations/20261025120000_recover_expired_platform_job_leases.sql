-- Recover expired leases after a worker dies on its final allowed attempt.
create or replace function public.claim_platform_job(p_lease_seconds integer default 120)
returns setof public.platform_jobs language plpgsql security definer set search_path = '' as $$
begin
 if p_lease_seconds < 30 or p_lease_seconds > 900 then raise exception 'lease duration must be between 30 and 900 seconds'; end if;
 with expired as (
  update public.platform_jobs set status='failed', error_code='worker_lease_expired', completed_at=now(), lease_expires_at=null, updated_at=now()
  where status='running' and lease_expires_at < now() and attempt_count >= max_attempts returning job_id
 )
 insert into public.platform_job_events(job_id,event_type,event_json)
 select job_id,'job_failed',jsonb_build_object('error_code','worker_lease_expired') from expired;
 return query with candidate as (
  select j.job_id from public.platform_jobs j
  where ((j.status='queued' and j.available_at <= now()) or (j.status='running' and j.lease_expires_at < now() and j.attempt_count < j.max_attempts))
  order by j.available_at asc,j.created_at asc for update skip locked limit 1
 ) update public.platform_jobs j set status='running',attempt_count=j.attempt_count+1,
  lease_expires_at=now()+make_interval(secs=>p_lease_seconds),updated_at=now(),error_code=null
 from candidate c where j.job_id=c.job_id returning j.*;
end; $$;
revoke all on function public.claim_platform_job(integer) from public, anon, authenticated;
grant execute on function public.claim_platform_job(integer) to service_role;
