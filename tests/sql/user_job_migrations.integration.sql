-- Disposable PostgreSQL integration checks for the user-job migrations.
-- Runs only in the ephemeral GitHub Actions PostgreSQL service.
begin;

do $$
declare
    user_a uuid := '11111111-1111-4111-8111-111111111111';
    user_b uuid := '22222222-2222-4222-8222-222222222222';
    job_a uuid := 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    job_done uuid := 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
    payload_json jsonb := '{"prompt":"integration test"}'::jsonb;
    result text;
begin
    if public.reserve_user_job_quota(user_a, 'key-1', 2, 3600) is not true then
        raise exception 'first quota reservation should succeed';
    end if;
    if public.reserve_user_job_quota(user_a, 'key-1', 2, 3600) is not true then
        raise exception 'same idempotency key should be accepted on retry';
    end if;
    if public.reserve_user_job_quota(user_a, 'key-2', 2, 3600) is not true then
        raise exception 'second unique quota reservation should succeed';
    end if;
    if public.reserve_user_job_quota(user_a, 'key-3', 2, 3600) is not false then
        raise exception 'quota limit should reject third unique reservation';
    end if;
    if public.reserve_user_job_quota(user_b, 'key-1', 2, 3600) is not true then
        raise exception 'quota must be isolated per tenant';
    end if;

    insert into public.platform_jobs(
        job_id, tenant_id, requested_by, job_type, status, payload,
        idempotency_key, payload_hash
    ) values (
        job_a, user_a::text, user_a::text, 'intelligence.solve', 'queued',
        payload_json, 'job-a', 'hash-a'
    );

    result := public.cancel_user_platform_job(job_a, user_b);
    if result <> 'not_found' then
        raise exception 'cross-tenant cancellation must be indistinguishable from missing job, got %', result;
    end if;
    if (select status from public.platform_jobs where job_id = job_a) <> 'queued' then
        raise exception 'cross-tenant cancellation changed the job';
    end if;

    result := public.cancel_user_platform_job(job_a, user_a);
    if result <> 'cancelled' then
        raise exception 'owner cancellation should succeed, got %', result;
    end if;
    if (select status from public.platform_jobs where job_id = job_a) <> 'cancelled' then
        raise exception 'owner cancellation did not persist status';
    end if;
    if (select error_code from public.platform_jobs where job_id = job_a) <> 'user_cancelled' then
        raise exception 'owner cancellation error marker missing';
    end if;

    insert into public.platform_jobs(
        job_id, tenant_id, requested_by, job_type, status, payload,
        idempotency_key, payload_hash
    ) values (
        job_done, user_a::text, user_a::text, 'intelligence.solve', 'succeeded',
        payload_json, 'job-done', 'hash-done'
    );
    result := public.cancel_user_platform_job(job_done, user_a);
    if result <> 'not_cancellable' then
        raise exception 'terminal job must not be cancellable, got %', result;
    end if;

    if has_function_privilege('anon', 'public.cancel_user_platform_job(uuid,uuid)', 'EXECUTE') then
        raise exception 'anon must not execute cancellation RPC';
    end if;
    if has_function_privilege('authenticated', 'public.cancel_user_platform_job(uuid,uuid)', 'EXECUTE') then
        raise exception 'authenticated must not execute cancellation RPC directly';
    end if;
    if not has_function_privilege('service_role', 'public.cancel_user_platform_job(uuid,uuid)', 'EXECUTE') then
        raise exception 'service_role must execute cancellation RPC';
    end if;
    if has_function_privilege('anon', 'public.reserve_user_job_quota(uuid,text,integer,integer)', 'EXECUTE') then
        raise exception 'anon must not execute quota RPC';
    end if;
    if has_function_privilege('authenticated', 'public.reserve_user_job_quota(uuid,text,integer,integer)', 'EXECUTE') then
        raise exception 'authenticated must not execute quota RPC directly';
    end if;
end $$;

rollback;
