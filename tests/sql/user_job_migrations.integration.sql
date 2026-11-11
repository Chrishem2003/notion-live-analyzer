-- Disposable PostgreSQL integration checks for the user-job migrations.
-- Runs only in the ephemeral GitHub Actions PostgreSQL service.
begin;

do $$
declare
    user_a uuid := '11111111-1111-4111-8111-111111111111';
    user_b uuid := '22222222-2222-4222-8222-222222222222';
    job_a uuid := 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    job_done uuid := 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
    job_retry uuid := 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
    job_lease uuid := 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';
    claimed public.platform_jobs;
    changed boolean;
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

    -- A late worker completion must not resurrect a cancelled job or persist output.
    changed := public.finish_platform_job(job_a, '{"answer":"late provider response"}'::jsonb);
    if changed is not false then
        raise exception 'late completion of cancelled job must be rejected';
    end if;
    if (select result_json from public.platform_jobs where job_id = job_a) is not null then
        raise exception 'late completion wrote a result to cancelled job';
    end if;

    -- A failed attempt is rescheduled, then reaches terminal failure at max_attempts.
    insert into public.platform_jobs(
        job_id, tenant_id, requested_by, job_type, status, payload,
        idempotency_key, payload_hash, max_attempts
    ) values (
        job_retry, user_a::text, user_a::text, 'intelligence.solve', 'queued',
        payload_json, 'job-retry', 'hash-retry', 2
    );
    select * into claimed from public.claim_platform_job(30);
    if claimed.job_id <> job_retry or claimed.status <> 'running' or claimed.attempt_count <> 1 then
        raise exception 'first queued job claim failed or attempt count is wrong';
    end if;
    changed := public.fail_platform_job(job_retry, 'integration_error', 0);
    if changed is not true then
        raise exception 'first failure should schedule retry';
    end if;
    if (select status from public.platform_jobs where job_id = job_retry) <> 'queued' then
        raise exception 'first failure should return job to queue';
    end if;
    select * into claimed from public.claim_platform_job(30);
    if claimed.job_id <> job_retry or claimed.attempt_count <> 2 then
        raise exception 'retry claim should increment attempt count';
    end if;
    changed := public.fail_platform_job(job_retry, 'integration_error', 0);
    if changed is not true then
        raise exception 'second failure should be recorded';
    end if;
    if (select status from public.platform_jobs where job_id = job_retry) <> 'failed' then
        raise exception 'job should become terminal after max_attempts';
    end if;
    changed := public.finish_platform_job(job_retry, '{"answer":"must not overwrite failure"}'::jsonb);
    if changed is not false then
        raise exception 'late completion must not overwrite terminal failure';
    end if;

    -- An expired running lease is recoverable by a later worker.
    insert into public.platform_jobs(
        job_id, tenant_id, requested_by, job_type, status, payload,
        idempotency_key, payload_hash, attempt_count, max_attempts, lease_expires_at
    ) values (
        job_lease, user_a::text, user_a::text, 'intelligence.solve', 'running',
        payload_json, 'job-lease', 'hash-lease', 1, 3, now() - interval '1 minute'
    );
    select * into claimed from public.claim_platform_job(30);
    if claimed.job_id <> job_lease or claimed.status <> 'running' or claimed.attempt_count <> 2 then
        raise exception 'expired lease was not recovered with incremented attempt count';
    end if;
    changed := public.finish_platform_job(job_lease, '{"answer":"completed after recovery"}'::jsonb);
    if changed is not true then
        raise exception 'recovered job should finish successfully';
    end if;
    if (select status from public.platform_jobs where job_id = job_lease) <> 'succeeded' then
        raise exception 'recovered job result did not persist';
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
