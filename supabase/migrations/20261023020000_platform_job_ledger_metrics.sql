-- Aggregate-only operational visibility for the durable platform job ledger.
-- Never returns payloads, actor identifiers, job IDs, error bodies, or secrets.

create or replace function public.platform_get_job_metrics()
returns jsonb
language sql
security definer
set search_path = pg_catalog, public
as $$
    select jsonb_build_object(
        'total', count(*),
        'queued', count(*) filter (where status = 'queued'),
        'running', count(*) filter (where status = 'running'),
        'succeeded', count(*) filter (where status = 'succeeded'),
        'failed', count(*) filter (where status = 'failed'),
        'needs_review', count(*) filter (where status = 'needs_review'),
        'expired_leases', count(*) filter (
            where status = 'running' and lease_until < now()
        ),
        'oldest_queued_age_seconds', coalesce(
            floor(extract(epoch from (now() - min(created_at) filter (where status = 'queued'))))::bigint,
            0
        ),
        'created_last_24h', count(*) filter (where created_at >= now() - interval '24 hours'),
        'finished_last_24h', count(*) filter (
            where finished_at >= now() - interval '24 hours'
              and status in ('succeeded', 'failed', 'needs_review')
        ),
        'sampled_at', now()
    )
    from public.platform_jobs;
$$;

revoke all on function public.platform_get_job_metrics() from public, anon, authenticated;
grant execute on function public.platform_get_job_metrics() to service_role;
