-- Record queue submission in the append-only job event stream.
create or replace function public.log_platform_job_queued()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
 insert into public.platform_job_events(job_id,event_type,event_json)
 values (new.job_id,'job_queued',jsonb_build_object('job_type',new.job_type,'max_attempts',new.max_attempts));
 return new;
end; $$;
revoke all on function public.log_platform_job_queued() from public, anon, authenticated;
drop trigger if exists platform_jobs_log_queued on public.platform_jobs;
create trigger platform_jobs_log_queued after insert on public.platform_jobs for each row execute function public.log_platform_job_queued();
