-- Redact stored prompts and answers after 30 days while retaining job metadata.
-- This is a privacy control, not a substitute for per-user authorization.
create extension if not exists pg_cron with schema pg_catalog;

create or replace function public.redact_expired_platform_job_content()
returns bigint
language plpgsql
security definer
set search_path = pg_catalog, public
as $function$
declare
    redacted_count bigint := 0;
begin
    with expired as (
        update public.platform_jobs
        set
            status = case
                when status in ('queued', 'running') then 'failed'
                else status
            end,
            error_code = case
                when status in ('queued', 'running') then 'retention_expired'
                else error_code
            end,
            payload = jsonb_build_object('redacted', true),
            result_json = case
                when result_json is null then null
                else jsonb_build_object('redacted', true)
            end,
            completed_at = coalesce(completed_at, now()),
            lease_expires_at = null,
            updated_at = now()
        where created_at < now() - interval '30 days'
          and (
              payload <> '{"redacted": true}'::jsonb
              or (
                  result_json is not null
                  and result_json <> '{"redacted": true}'::jsonb
              )
              or status in ('queued', 'running')
          )
        returning job_id
    )
    insert into public.platform_job_events (job_id, event_type, event_json)
    select
        job_id,
        'content_redacted',
        jsonb_build_object('reason', 'retention_policy', 'retention_days', 30)
    from expired;

    get diagnostics redacted_count = row_count;
    return redacted_count;
end;
$function$;

revoke all on function public.redact_expired_platform_job_content() from public, anon, authenticated;
grant execute on function public.redact_expired_platform_job_content() to service_role;

select cron.schedule(
    'redact-expired-platform-job-content',
    '17 3 * * *',
    'select public.redact_expired_platform_job_content();'
);
