-- Tenant-scoped cancellation for user-facing durable jobs.
-- Draft only: apply to isolated staging after review, never production directly.
create or replace function public.cancel_user_platform_job(
    p_job_id uuid,
    p_tenant_id uuid
) returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
    current_status text;
begin
    if p_job_id is null or p_tenant_id is null then
        raise exception 'job and tenant ids are required';
    end if;

    update public.platform_jobs
       set status = 'cancelled',
           error_code = 'user_cancelled',
           result_json = null,
           completed_at = pg_catalog.now(),
           updated_at = pg_catalog.now(),
           lease_expires_at = null
     where job_id = p_job_id
       and tenant_id = p_tenant_id::text
       and status in ('queued', 'running');

    if found then
        return 'cancelled';
    end if;

    select j.status into current_status
      from public.platform_jobs j
     where j.job_id = p_job_id
       and j.tenant_id = p_tenant_id::text
     limit 1;

    if not found then
        -- Same response for a nonexistent job and another user's job.
        return 'not_found';
    end if;

    return 'not_cancellable';
end;
$$;

revoke all on function public.cancel_user_platform_job(uuid, uuid) from public, anon, authenticated;
grant execute on function public.cancel_user_platform_job(uuid, uuid) to service_role;
