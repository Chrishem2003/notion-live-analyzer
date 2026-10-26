-- NEMA-AGORA transactional measurement submission RPC (PROPOSED; NOT APPLIED).
-- Apply only after migration 004 is approved and installed in an isolated test project.
-- Caller must be the trusted API using its server-side service_role credential.
-- Never expose this RPC directly to browser/Streamlit clients.
-- p_actor_id and p_actor_role MUST be derived by the trusted API from authenticated identity,
-- not copied from user-supplied request fields. The database computes the payload digest from
-- PostgreSQL's canonical jsonb text representation of {measurement_id, record}; callers cannot supply it.

begin;

-- Dedicated non-login owner for the SECURITY DEFINER RPC. It is deliberately not
-- granted BYPASSRLS and is not a member of service_role or any login role.
do $role$
begin
    if not exists (select 1 from pg_catalog.pg_roles where rolname = 'nema_measurement_writer') then
        create role nema_measurement_writer nologin noinherit;
    end if;
end;
$role$;

-- Normalize an existing role too; CREATE ROLE IF NOT EXISTS alone would not
-- correct unsafe attributes if this name already existed in the target project.
alter role nema_measurement_writer
    nologin noinherit nosuperuser nocreatedb nocreaterole noreplication nobypassrls;

do $membership_guard$
begin
    if exists (
        select 1
          from pg_catalog.pg_auth_members
         where roleid = (select oid from pg_catalog.pg_roles where rolname = 'nema_measurement_writer')
            or member = (select oid from pg_catalog.pg_roles where rolname = 'nema_measurement_writer')
    ) then
        raise exception 'nema_measurement_writer must have no role memberships before migration';
    end if;
end;
$membership_guard$;

create table if not exists public.nema_measurement_idempotency (
    idempotency_key text primary key,
    payload_sha256 text not null check (payload_sha256 ~ '^[a-fA-F0-9]{64}$'),
    measurement_id text not null unique
        references public.nema_indicator_measurements(measurement_id) on delete restrict,
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_measurement_idempotency_key_nonblank
        check (length(pg_catalog.btrim(idempotency_key)) between 1 and 256)
);

create table if not exists public.nema_evidence_artifacts (
    evidence_id text primary key,
    measurement_id text not null
        references public.nema_indicator_measurements(measurement_id) on delete restrict,
    bucket_name text not null check (bucket_name ~ '^[a-z0-9][a-z0-9._-]{1,62}
    measurement_id text not null
        references public.nema_indicator_measurements(measurement_id) on delete restrict,
    actor_id text not null,
    actor_role text not null,
    action text not null check (action = 'measurement_submitted'),
    idempotency_key text not null
        references public.nema_measurement_idempotency(idempotency_key) on delete restrict,
    payload_sha256 text not null check (payload_sha256 ~ '^[a-fA-F0-9]{64}$'),
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_measurement_audit_actor_nonblank check (length(pg_catalog.btrim(actor_id)) > 0)
);

create index if not exists idx_nema_measurement_audit_measurement_created
    on public.nema_measurement_audit (measurement_id, created_at, audit_id);

alter table public.nema_measurement_idempotency enable row level security;
alter table public.nema_measurement_audit enable row level security;
alter table public.nema_evidence_artifacts enable row level security;

create or replace function public.reject_nema_measurement_audit_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
begin
    raise exception 'NEMA measurement audit events are append-only';
end;
$function$;

drop trigger if exists nema_measurement_audit_no_update on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_update
before update on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

drop trigger if exists nema_measurement_audit_no_delete on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_delete
before delete on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

create or replace function public.submit_nema_indicator_measurement(
    p_measurement_id text,
    p_idempotency_key text,
    p_actor_id text,
    p_actor_role text,
    p_record jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_existing public.nema_measurement_idempotency%rowtype;
    v_value numeric;
    v_numerator numeric;
    v_denominator numeric;
    v_decision text;
    v_payload_sha256 text;
begin
    if p_measurement_id is null or length(pg_catalog.btrim(p_measurement_id)) = 0
       or length(pg_catalog.btrim(p_measurement_id)) > 256 then
        raise exception 'invalid measurement id' using errcode = '22023';
    end if;
    if p_idempotency_key is null or length(pg_catalog.btrim(p_idempotency_key)) = 0
       or length(pg_catalog.btrim(p_idempotency_key)) > 256 then
        raise exception 'invalid idempotency key' using errcode = '22023';
    end if;
    if p_actor_id is null or length(pg_catalog.btrim(p_actor_id)) = 0
       or length(pg_catalog.btrim(p_actor_id)) > 256 then
        raise exception 'invalid trusted actor id' using errcode = '22023';
    end if;
    -- NULL must be rejected explicitly: SQL three-valued logic makes `NULL NOT IN (...)` NULL, not TRUE.
    if p_actor_role is null or p_actor_role not in ('submitter', 'coordinator', 'admin') then
        raise exception 'actor role is not allowed to submit measurements' using errcode = '42501';
    end if;
    if p_record is null or pg_catalog.jsonb_typeof(p_record) <> 'object' then
        raise exception 'measurement record must be a JSON object' using errcode = '22023';
    end if;
    if p_record->>'status' is distinct from 'measured' then
        raise exception 'submission status must be measured; verification is a separate review action'
            using errcode = '22023';
    end if;
    if p_record->>'indicator_id' is null or length(pg_catalog.btrim(p_record->>'indicator_id')) = 0
       or p_record->>'definition_version' is null
       or length(pg_catalog.btrim(p_record->>'definition_version')) = 0
       or p_record->>'reporting_timezone' is null
       or length(pg_catalog.btrim(p_record->>'reporting_timezone')) = 0
       or p_record->>'unit' is null
       or length(pg_catalog.btrim(p_record->>'unit')) = 0
       or p_record->>'calculation_method' is null
       or length(pg_catalog.btrim(p_record->>'calculation_method')) = 0
       or p_record->>'reporting_period_start' is null
       or p_record->>'reporting_period_end' is null then
        raise exception 'required measurement fields are missing' using errcode = '22023';
    end if;
    -- IS DISTINCT FROM rejects SQL NULL as well as JSON values of the wrong type.
    -- Keep array length in a separate branch so it is never evaluated on a non-array.
    if pg_catalog.jsonb_typeof(p_record->'source_refs') is distinct from 'array' then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'source_refs') = 0 then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
         where pg_catalog.jsonb_typeof(source_ref.item) is distinct from 'string'
            or length(pg_catalog.btrim(source_ref.item #>> '{}')) = 0
    ) then
        raise exception 'source_refs entries must be non-empty strings' using errcode = '22023';
    end if;
    if (
        select count(*) <> count(distinct source_ref.item #>> '{}')
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
    ) then
        raise exception 'source_refs entries must be unique' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_typeof(p_record->'evidence_refs') is distinct from 'array' then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'evidence_refs') = 0 then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'evidence_refs') as evidence_ref(item)
         where pg_catalog.jsonb_typeof(evidence_ref.item) is distinct from 'object'
            or pg_catalog.jsonb_typeof(evidence_ref.item->'reference') is distinct from 'string'
            or length(pg_catalog.btrim(evidence_ref.item->>'reference')) = 0
            or pg_catalog.jsonb_typeof(evidence_ref.item->'sha256') is distinct from 'string'
            or (evidence_ref.item->>'sha256') !~ '^[A-Fa-f0-9]{64}
        raise exception 'evidence_refs require a reference and a valid SHA-256 digest' using errcode = '22023';
    end if;
    if p_record ? 'exclusions' and pg_catalog.jsonb_typeof(p_record->'exclusions') is distinct from 'array' then
        raise exception 'exclusions must be an array' using errcode = '22023';
    end if;
    if p_record ? 'caveats' and pg_catalog.jsonb_typeof(p_record->'caveats') is distinct from 'array' then
        raise exception 'caveats must be an array' using errcode = '22023';
    end if;

    begin
        v_value := (p_record->>'value')::numeric;
        if p_record ? 'numerator' then v_numerator := (p_record->>'numerator')::numeric; end if;
        if p_record ? 'denominator' then v_denominator := (p_record->>'denominator')::numeric; end if;
    exception when others then
        raise exception 'value, numerator, or denominator is not numeric' using errcode = '22023';
    end;
    if v_value is null or v_value < 0 or v_value = 'NaN'::numeric
       or v_value = 'Infinity'::numeric or v_value = '-Infinity'::numeric then
        raise exception 'value must be a finite non-negative number' using errcode = '22023';
    end if;
    if v_numerator is not null and (v_numerator < 0 or v_numerator = 'NaN'::numeric
       or v_numerator = 'Infinity'::numeric or v_numerator = '-Infinity'::numeric) then
        raise exception 'numerator must be finite and non-negative' using errcode = '22023';
    end if;
    if v_denominator is not null and (v_denominator <= 0 or v_denominator = 'NaN'::numeric
       or v_denominator = 'Infinity'::numeric or v_denominator = '-Infinity'::numeric) then
        raise exception 'denominator must be finite and positive' using errcode = '22023';
    end if;
    if v_numerator is not null and v_denominator is not null and v_numerator > v_denominator then
        raise exception 'numerator cannot exceed denominator' using errcode = '22023';
    end if;
    begin
        if (p_record->>'reporting_period_start')::date > (p_record->>'reporting_period_end')::date then
            raise exception 'reporting period end precedes start' using errcode = '22023';
        end if;
    exception when sqlstate '22023' then
        raise;
    when others then
        raise exception 'reporting period dates must be valid ISO dates' using errcode = '22023';
    end;

    -- Compute the digest inside PostgreSQL from the actual database payload. jsonb::text has
    -- deterministic key ordering and formatting within PostgreSQL; the API must not supply a digest.
    v_payload_sha256 := pg_catalog.encode(
        extensions.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Serialize requests using the same key so concurrent retries cannot both create a record.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_idempotency_key, 0)
    );
    select * into v_existing
      from public.nema_measurement_idempotency
     where idempotency_key = p_idempotency_key;
    if found then
        if pg_catalog.lower(v_existing.payload_sha256) <> v_payload_sha256 then
            raise exception 'idempotency key reused with a different payload' using errcode = '23505';
        end if;
        return pg_catalog.jsonb_build_object(
            'decision', 'replay',
            'measurement_id', v_existing.measurement_id,
            'payload_sha256', v_existing.payload_sha256,
            'audit_created', false
        );
    end if;

    insert into public.nema_indicator_measurements (
        measurement_id, indicator_id, definition_version, reporting_period_start,
        reporting_period_end, reporting_timezone, status, value, unit, numerator,
        denominator, exclusions, source_refs, evidence_refs, calculation_method,
        reviewer_id, verified_at, caveats
    ) values (
        p_measurement_id, p_record->>'indicator_id', p_record->>'definition_version',
        (p_record->>'reporting_period_start')::date, (p_record->>'reporting_period_end')::date,
        p_record->>'reporting_timezone', 'measured', v_value, p_record->>'unit',
        v_numerator, v_denominator,
        coalesce(p_record->'exclusions', '[]'::jsonb),
        p_record->'source_refs', coalesce(p_record->'evidence_refs', '[]'::jsonb),
        p_record->>'calculation_method', null, null, coalesce(p_record->'caveats', '[]'::jsonb)
    );

    -- Register storage provenance in this same transaction. The trusted API must
    -- construct each reference only after Supabase Storage read-back digest verification.
    insert into public.nema_evidence_artifacts (
        evidence_id, measurement_id, bucket_name, object_key, sha256, registered_by
    )
    select
        p_measurement_id || ':' || pg_catalog.lower(evidence_ref.item->>'sha256'),
        p_measurement_id,
        split_part(evidence_ref.item->>'reference', '/', 1),
        substr(evidence_ref.item->>'reference', length(split_part(evidence_ref.item->>'reference', '/', 1)) + 2),
        pg_catalog.lower(evidence_ref.item->>'sha256'),
        p_actor_id
    from pg_catalog.jsonb_array_elements(p_record->'evidence_refs') as evidence_ref(item);

    insert into public.nema_measurement_idempotency (
        idempotency_key, payload_sha256, measurement_id
    ) values (p_idempotency_key, v_payload_sha256, p_measurement_id);

    insert into public.nema_measurement_audit (
        audit_id, measurement_id, actor_id, actor_role, action, idempotency_key, payload_sha256
    ) values (
        p_measurement_id || ':submitted', p_measurement_id, p_actor_id, p_actor_role,
        'measurement_submitted', p_idempotency_key, v_payload_sha256
    );

    return pg_catalog.jsonb_build_object(
        'decision', 'new',
        'measurement_id', p_measurement_id,
        'payload_sha256', v_payload_sha256,
        'audit_created', true
    );
end;
$function$;

revoke all on table public.nema_measurement_idempotency from anon, authenticated, service_role;
revoke all on table public.nema_measurement_audit from anon, authenticated, service_role;
revoke all on table public.nema_evidence_artifacts from anon, authenticated, service_role;
revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;

-- The function owner has only the table rights the RPC needs. RLS remains enabled;
-- policies below are scoped only to this non-login role. No direct client policies exist.
grant usage on schema public to nema_measurement_writer;
grant usage on schema extensions to nema_measurement_writer;
grant select, insert on table public.nema_indicator_measurements to nema_measurement_writer;
grant select, insert on table public.nema_measurement_idempotency to nema_measurement_writer;
grant insert on table public.nema_measurement_audit to nema_measurement_writer;
grant insert on table public.nema_evidence_artifacts to nema_measurement_writer;

drop policy if exists nema_measurement_writer_access on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_select on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_insert on public.nema_indicator_measurements;
create policy nema_measurement_writer_select on public.nema_indicator_measurements
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_indicator_measurements
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_select on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_idempotency;
create policy nema_measurement_writer_select on public.nema_measurement_idempotency
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_measurement_idempotency
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_audit;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_audit;
create policy nema_measurement_writer_insert on public.nema_measurement_audit
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_insert on public.nema_evidence_artifacts;
create policy nema_measurement_writer_insert on public.nema_evidence_artifacts
    for insert to nema_measurement_writer with check (true);

grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;
grant execute on function extensions.digest(bytea, text) to nema_measurement_writer;
grant select on table public.nema_measurement_idempotency to service_role;
grant select on table public.nema_measurement_audit to service_role;
grant select on table public.nema_evidence_artifacts to service_role;

revoke all on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    from public, anon, authenticated, service_role;

-- PostgreSQL requires the target owner to have CREATE on the containing schema
-- during ALTER FUNCTION OWNER. Grant it only for this ownership transfer, then
-- immediately revoke it so the SECURITY DEFINER owner cannot create schema objects.
grant create on schema public to nema_measurement_writer;
alter function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    owner to nema_measurement_writer;
revoke create on schema public from nema_measurement_writer;

grant execute on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    to service_role;

revoke all on function public.reject_nema_measurement_audit_mutation()
    from public, anon, authenticated, service_role;

commit;

-- REQUIRED before staging approval:
-- * Verify pgcrypto is installed in schema extensions before applying this migration.
-- * Validate database-computed digest parity and replay behavior on the target PostgreSQL version.
-- * Test concurrent duplicate requests, conflict, injected rollback, and unique-key collision.
-- * Verify function owner is nema_measurement_writer (NOLOGIN, NOINHERIT, no BYPASSRLS).
-- * Verify writer-role table grants and command-specific SELECT/INSERT RLS policies match this migration.
-- * Confirm RLS/grants and fixed search_path; verify no anon/authenticated execution.
-- * This RPC does not authenticate p_actor_id/p_actor_role; API must derive these from OIDC/session.
-- * Evidence bytes and reviewer independence require separate authenticated workflows.),
    object_key text not null,
    sha256 text not null check (sha256 ~ '^[a-fA-F0-9]{64}
    measurement_id text not null
        references public.nema_indicator_measurements(measurement_id) on delete restrict,
    actor_id text not null,
    actor_role text not null,
    action text not null check (action = 'measurement_submitted'),
    idempotency_key text not null
        references public.nema_measurement_idempotency(idempotency_key) on delete restrict,
    payload_sha256 text not null check (payload_sha256 ~ '^[a-fA-F0-9]{64}$'),
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_measurement_audit_actor_nonblank check (length(pg_catalog.btrim(actor_id)) > 0)
);

create index if not exists idx_nema_measurement_audit_measurement_created
    on public.nema_measurement_audit (measurement_id, created_at, audit_id);

alter table public.nema_measurement_idempotency enable row level security;
alter table public.nema_measurement_audit enable row level security;

create or replace function public.reject_nema_measurement_audit_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
begin
    raise exception 'NEMA measurement audit events are append-only';
end;
$function$;

drop trigger if exists nema_measurement_audit_no_update on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_update
before update on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

drop trigger if exists nema_measurement_audit_no_delete on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_delete
before delete on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

create or replace function public.submit_nema_indicator_measurement(
    p_measurement_id text,
    p_idempotency_key text,
    p_actor_id text,
    p_actor_role text,
    p_record jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_existing public.nema_measurement_idempotency%rowtype;
    v_value numeric;
    v_numerator numeric;
    v_denominator numeric;
    v_decision text;
    v_payload_sha256 text;
begin
    if p_measurement_id is null or length(pg_catalog.btrim(p_measurement_id)) = 0
       or length(pg_catalog.btrim(p_measurement_id)) > 256 then
        raise exception 'invalid measurement id' using errcode = '22023';
    end if;
    if p_idempotency_key is null or length(pg_catalog.btrim(p_idempotency_key)) = 0
       or length(pg_catalog.btrim(p_idempotency_key)) > 256 then
        raise exception 'invalid idempotency key' using errcode = '22023';
    end if;
    if p_actor_id is null or length(pg_catalog.btrim(p_actor_id)) = 0
       or length(pg_catalog.btrim(p_actor_id)) > 256 then
        raise exception 'invalid trusted actor id' using errcode = '22023';
    end if;
    -- NULL must be rejected explicitly: SQL three-valued logic makes `NULL NOT IN (...)` NULL, not TRUE.
    if p_actor_role is null or p_actor_role not in ('submitter', 'coordinator', 'admin') then
        raise exception 'actor role is not allowed to submit measurements' using errcode = '42501';
    end if;
    if p_record is null or pg_catalog.jsonb_typeof(p_record) <> 'object' then
        raise exception 'measurement record must be a JSON object' using errcode = '22023';
    end if;
    if p_record->>'status' is distinct from 'measured' then
        raise exception 'submission status must be measured; verification is a separate review action'
            using errcode = '22023';
    end if;
    if p_record->>'indicator_id' is null or length(pg_catalog.btrim(p_record->>'indicator_id')) = 0
       or p_record->>'definition_version' is null
       or length(pg_catalog.btrim(p_record->>'definition_version')) = 0
       or p_record->>'reporting_timezone' is null
       or length(pg_catalog.btrim(p_record->>'reporting_timezone')) = 0
       or p_record->>'unit' is null
       or length(pg_catalog.btrim(p_record->>'unit')) = 0
       or p_record->>'calculation_method' is null
       or length(pg_catalog.btrim(p_record->>'calculation_method')) = 0
       or p_record->>'reporting_period_start' is null
       or p_record->>'reporting_period_end' is null then
        raise exception 'required measurement fields are missing' using errcode = '22023';
    end if;
    -- IS DISTINCT FROM rejects SQL NULL as well as JSON values of the wrong type.
    -- Keep array length in a separate branch so it is never evaluated on a non-array.
    if pg_catalog.jsonb_typeof(p_record->'source_refs') is distinct from 'array' then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'source_refs') = 0 then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
         where pg_catalog.jsonb_typeof(source_ref.item) is distinct from 'string'
            or length(pg_catalog.btrim(source_ref.item #>> '{}')) = 0
    ) then
        raise exception 'source_refs entries must be non-empty strings' using errcode = '22023';
    end if;
    if (
        select count(*) <> count(distinct source_ref.item #>> '{}')
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
    ) then
        raise exception 'source_refs entries must be unique' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_typeof(p_record->'evidence_refs') is distinct from 'array' then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'evidence_refs') = 0 then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'evidence_refs') as evidence_ref(item)
         where pg_catalog.jsonb_typeof(evidence_ref.item) is distinct from 'object'
            or pg_catalog.jsonb_typeof(evidence_ref.item->'reference') is distinct from 'string'
            or length(pg_catalog.btrim(evidence_ref.item->>'reference')) = 0
            or pg_catalog.jsonb_typeof(evidence_ref.item->'sha256') is distinct from 'string'
            or (evidence_ref.item->>'sha256') !~ '^[A-Fa-f0-9]{64}$'
    ) then
        raise exception 'evidence_refs require a reference and a valid SHA-256 digest' using errcode = '22023';
    end if;
    if p_record ? 'exclusions' and pg_catalog.jsonb_typeof(p_record->'exclusions') is distinct from 'array' then
        raise exception 'exclusions must be an array' using errcode = '22023';
    end if;
    if p_record ? 'caveats' and pg_catalog.jsonb_typeof(p_record->'caveats') is distinct from 'array' then
        raise exception 'caveats must be an array' using errcode = '22023';
    end if;

    begin
        v_value := (p_record->>'value')::numeric;
        if p_record ? 'numerator' then v_numerator := (p_record->>'numerator')::numeric; end if;
        if p_record ? 'denominator' then v_denominator := (p_record->>'denominator')::numeric; end if;
    exception when others then
        raise exception 'value, numerator, or denominator is not numeric' using errcode = '22023';
    end;
    if v_value is null or v_value < 0 or v_value = 'NaN'::numeric
       or v_value = 'Infinity'::numeric or v_value = '-Infinity'::numeric then
        raise exception 'value must be a finite non-negative number' using errcode = '22023';
    end if;
    if v_numerator is not null and (v_numerator < 0 or v_numerator = 'NaN'::numeric
       or v_numerator = 'Infinity'::numeric or v_numerator = '-Infinity'::numeric) then
        raise exception 'numerator must be finite and non-negative' using errcode = '22023';
    end if;
    if v_denominator is not null and (v_denominator <= 0 or v_denominator = 'NaN'::numeric
       or v_denominator = 'Infinity'::numeric or v_denominator = '-Infinity'::numeric) then
        raise exception 'denominator must be finite and positive' using errcode = '22023';
    end if;
    if v_numerator is not null and v_denominator is not null and v_numerator > v_denominator then
        raise exception 'numerator cannot exceed denominator' using errcode = '22023';
    end if;
    begin
        if (p_record->>'reporting_period_start')::date > (p_record->>'reporting_period_end')::date then
            raise exception 'reporting period end precedes start' using errcode = '22023';
        end if;
    exception when sqlstate '22023' then
        raise;
    when others then
        raise exception 'reporting period dates must be valid ISO dates' using errcode = '22023';
    end;

    -- Compute the digest inside PostgreSQL from the actual database payload. jsonb::text has
    -- deterministic key ordering and formatting within PostgreSQL; the API must not supply a digest.
    v_payload_sha256 := pg_catalog.encode(
        extensions.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Serialize requests using the same key so concurrent retries cannot both create a record.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_idempotency_key, 0)
    );
    select * into v_existing
      from public.nema_measurement_idempotency
     where idempotency_key = p_idempotency_key;
    if found then
        if pg_catalog.lower(v_existing.payload_sha256) <> v_payload_sha256 then
            raise exception 'idempotency key reused with a different payload' using errcode = '23505';
        end if;
        return pg_catalog.jsonb_build_object(
            'decision', 'replay',
            'measurement_id', v_existing.measurement_id,
            'payload_sha256', v_existing.payload_sha256,
            'audit_created', false
        );
    end if;

    insert into public.nema_indicator_measurements (
        measurement_id, indicator_id, definition_version, reporting_period_start,
        reporting_period_end, reporting_timezone, status, value, unit, numerator,
        denominator, exclusions, source_refs, evidence_refs, calculation_method,
        reviewer_id, verified_at, caveats
    ) values (
        p_measurement_id, p_record->>'indicator_id', p_record->>'definition_version',
        (p_record->>'reporting_period_start')::date, (p_record->>'reporting_period_end')::date,
        p_record->>'reporting_timezone', 'measured', v_value, p_record->>'unit',
        v_numerator, v_denominator,
        coalesce(p_record->'exclusions', '[]'::jsonb),
        p_record->'source_refs', coalesce(p_record->'evidence_refs', '[]'::jsonb),
        p_record->>'calculation_method', null, null, coalesce(p_record->'caveats', '[]'::jsonb)
    );

    insert into public.nema_measurement_idempotency (
        idempotency_key, payload_sha256, measurement_id
    ) values (p_idempotency_key, v_payload_sha256, p_measurement_id);

    insert into public.nema_measurement_audit (
        audit_id, measurement_id, actor_id, actor_role, action, idempotency_key, payload_sha256
    ) values (
        p_measurement_id || ':submitted', p_measurement_id, p_actor_id, p_actor_role,
        'measurement_submitted', p_idempotency_key, v_payload_sha256
    );

    return pg_catalog.jsonb_build_object(
        'decision', 'new',
        'measurement_id', p_measurement_id,
        'payload_sha256', v_payload_sha256,
        'audit_created', true
    );
end;
$function$;

revoke all on table public.nema_measurement_idempotency from anon, authenticated, service_role;
revoke all on table public.nema_measurement_audit from anon, authenticated, service_role;
revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;

-- The function owner has only the table rights the RPC needs. RLS remains enabled;
-- policies below are scoped only to this non-login role. No direct client policies exist.
grant usage on schema public to nema_measurement_writer;
grant usage on schema extensions to nema_measurement_writer;
grant select, insert on table public.nema_indicator_measurements to nema_measurement_writer;
grant select, insert on table public.nema_measurement_idempotency to nema_measurement_writer;
grant insert on table public.nema_measurement_audit to nema_measurement_writer;

drop policy if exists nema_measurement_writer_access on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_select on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_insert on public.nema_indicator_measurements;
create policy nema_measurement_writer_select on public.nema_indicator_measurements
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_indicator_measurements
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_select on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_idempotency;
create policy nema_measurement_writer_select on public.nema_measurement_idempotency
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_measurement_idempotency
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_audit;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_audit;
create policy nema_measurement_writer_insert on public.nema_measurement_audit
    for insert to nema_measurement_writer with check (true);

grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;
grant execute on function extensions.digest(bytea, text) to nema_measurement_writer;
grant select on table public.nema_measurement_idempotency to service_role;
grant select on table public.nema_measurement_audit to service_role;

revoke all on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    from public, anon, authenticated, service_role;

-- PostgreSQL requires the target owner to have CREATE on the containing schema
-- during ALTER FUNCTION OWNER. Grant it only for this ownership transfer, then
-- immediately revoke it so the SECURITY DEFINER owner cannot create schema objects.
grant create on schema public to nema_measurement_writer;
alter function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    owner to nema_measurement_writer;
revoke create on schema public from nema_measurement_writer;

grant execute on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    to service_role;

revoke all on function public.reject_nema_measurement_audit_mutation()
    from public, anon, authenticated, service_role;

commit;

-- REQUIRED before staging approval:
-- * Verify pgcrypto is installed in schema extensions before applying this migration.
-- * Validate database-computed digest parity and replay behavior on the target PostgreSQL version.
-- * Test concurrent duplicate requests, conflict, injected rollback, and unique-key collision.
-- * Verify function owner is nema_measurement_writer (NOLOGIN, NOINHERIT, no BYPASSRLS).
-- * Verify writer-role table grants and command-specific SELECT/INSERT RLS policies match this migration.
-- * Confirm RLS/grants and fixed search_path; verify no anon/authenticated execution.
-- * This RPC does not authenticate p_actor_id/p_actor_role; API must derive these from OIDC/session.
-- * Evidence bytes and reviewer independence require separate authenticated workflows.),
    registered_by text not null,
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_evidence_bucket_object_unique unique (bucket_name, object_key),
    constraint nema_evidence_object_key_shape check (
        object_key ~ '^sha256/[0-9a-f]{2}/[0-9a-f]{64}
    measurement_id text not null
        references public.nema_indicator_measurements(measurement_id) on delete restrict,
    actor_id text not null,
    actor_role text not null,
    action text not null check (action = 'measurement_submitted'),
    idempotency_key text not null
        references public.nema_measurement_idempotency(idempotency_key) on delete restrict,
    payload_sha256 text not null check (payload_sha256 ~ '^[a-fA-F0-9]{64}$'),
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_measurement_audit_actor_nonblank check (length(pg_catalog.btrim(actor_id)) > 0)
);

create index if not exists idx_nema_measurement_audit_measurement_created
    on public.nema_measurement_audit (measurement_id, created_at, audit_id);

alter table public.nema_measurement_idempotency enable row level security;
alter table public.nema_measurement_audit enable row level security;

create or replace function public.reject_nema_measurement_audit_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
begin
    raise exception 'NEMA measurement audit events are append-only';
end;
$function$;

drop trigger if exists nema_measurement_audit_no_update on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_update
before update on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

drop trigger if exists nema_measurement_audit_no_delete on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_delete
before delete on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

create or replace function public.submit_nema_indicator_measurement(
    p_measurement_id text,
    p_idempotency_key text,
    p_actor_id text,
    p_actor_role text,
    p_record jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_existing public.nema_measurement_idempotency%rowtype;
    v_value numeric;
    v_numerator numeric;
    v_denominator numeric;
    v_decision text;
    v_payload_sha256 text;
begin
    if p_measurement_id is null or length(pg_catalog.btrim(p_measurement_id)) = 0
       or length(pg_catalog.btrim(p_measurement_id)) > 256 then
        raise exception 'invalid measurement id' using errcode = '22023';
    end if;
    if p_idempotency_key is null or length(pg_catalog.btrim(p_idempotency_key)) = 0
       or length(pg_catalog.btrim(p_idempotency_key)) > 256 then
        raise exception 'invalid idempotency key' using errcode = '22023';
    end if;
    if p_actor_id is null or length(pg_catalog.btrim(p_actor_id)) = 0
       or length(pg_catalog.btrim(p_actor_id)) > 256 then
        raise exception 'invalid trusted actor id' using errcode = '22023';
    end if;
    -- NULL must be rejected explicitly: SQL three-valued logic makes `NULL NOT IN (...)` NULL, not TRUE.
    if p_actor_role is null or p_actor_role not in ('submitter', 'coordinator', 'admin') then
        raise exception 'actor role is not allowed to submit measurements' using errcode = '42501';
    end if;
    if p_record is null or pg_catalog.jsonb_typeof(p_record) <> 'object' then
        raise exception 'measurement record must be a JSON object' using errcode = '22023';
    end if;
    if p_record->>'status' is distinct from 'measured' then
        raise exception 'submission status must be measured; verification is a separate review action'
            using errcode = '22023';
    end if;
    if p_record->>'indicator_id' is null or length(pg_catalog.btrim(p_record->>'indicator_id')) = 0
       or p_record->>'definition_version' is null
       or length(pg_catalog.btrim(p_record->>'definition_version')) = 0
       or p_record->>'reporting_timezone' is null
       or length(pg_catalog.btrim(p_record->>'reporting_timezone')) = 0
       or p_record->>'unit' is null
       or length(pg_catalog.btrim(p_record->>'unit')) = 0
       or p_record->>'calculation_method' is null
       or length(pg_catalog.btrim(p_record->>'calculation_method')) = 0
       or p_record->>'reporting_period_start' is null
       or p_record->>'reporting_period_end' is null then
        raise exception 'required measurement fields are missing' using errcode = '22023';
    end if;
    -- IS DISTINCT FROM rejects SQL NULL as well as JSON values of the wrong type.
    -- Keep array length in a separate branch so it is never evaluated on a non-array.
    if pg_catalog.jsonb_typeof(p_record->'source_refs') is distinct from 'array' then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'source_refs') = 0 then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
         where pg_catalog.jsonb_typeof(source_ref.item) is distinct from 'string'
            or length(pg_catalog.btrim(source_ref.item #>> '{}')) = 0
    ) then
        raise exception 'source_refs entries must be non-empty strings' using errcode = '22023';
    end if;
    if (
        select count(*) <> count(distinct source_ref.item #>> '{}')
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
    ) then
        raise exception 'source_refs entries must be unique' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_typeof(p_record->'evidence_refs') is distinct from 'array' then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'evidence_refs') = 0 then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'evidence_refs') as evidence_ref(item)
         where pg_catalog.jsonb_typeof(evidence_ref.item) is distinct from 'object'
            or pg_catalog.jsonb_typeof(evidence_ref.item->'reference') is distinct from 'string'
            or length(pg_catalog.btrim(evidence_ref.item->>'reference')) = 0
            or pg_catalog.jsonb_typeof(evidence_ref.item->'sha256') is distinct from 'string'
            or (evidence_ref.item->>'sha256') !~ '^[A-Fa-f0-9]{64}$'
    ) then
        raise exception 'evidence_refs require a reference and a valid SHA-256 digest' using errcode = '22023';
    end if;
    if p_record ? 'exclusions' and pg_catalog.jsonb_typeof(p_record->'exclusions') is distinct from 'array' then
        raise exception 'exclusions must be an array' using errcode = '22023';
    end if;
    if p_record ? 'caveats' and pg_catalog.jsonb_typeof(p_record->'caveats') is distinct from 'array' then
        raise exception 'caveats must be an array' using errcode = '22023';
    end if;

    begin
        v_value := (p_record->>'value')::numeric;
        if p_record ? 'numerator' then v_numerator := (p_record->>'numerator')::numeric; end if;
        if p_record ? 'denominator' then v_denominator := (p_record->>'denominator')::numeric; end if;
    exception when others then
        raise exception 'value, numerator, or denominator is not numeric' using errcode = '22023';
    end;
    if v_value is null or v_value < 0 or v_value = 'NaN'::numeric
       or v_value = 'Infinity'::numeric or v_value = '-Infinity'::numeric then
        raise exception 'value must be a finite non-negative number' using errcode = '22023';
    end if;
    if v_numerator is not null and (v_numerator < 0 or v_numerator = 'NaN'::numeric
       or v_numerator = 'Infinity'::numeric or v_numerator = '-Infinity'::numeric) then
        raise exception 'numerator must be finite and non-negative' using errcode = '22023';
    end if;
    if v_denominator is not null and (v_denominator <= 0 or v_denominator = 'NaN'::numeric
       or v_denominator = 'Infinity'::numeric or v_denominator = '-Infinity'::numeric) then
        raise exception 'denominator must be finite and positive' using errcode = '22023';
    end if;
    if v_numerator is not null and v_denominator is not null and v_numerator > v_denominator then
        raise exception 'numerator cannot exceed denominator' using errcode = '22023';
    end if;
    begin
        if (p_record->>'reporting_period_start')::date > (p_record->>'reporting_period_end')::date then
            raise exception 'reporting period end precedes start' using errcode = '22023';
        end if;
    exception when sqlstate '22023' then
        raise;
    when others then
        raise exception 'reporting period dates must be valid ISO dates' using errcode = '22023';
    end;

    -- Compute the digest inside PostgreSQL from the actual database payload. jsonb::text has
    -- deterministic key ordering and formatting within PostgreSQL; the API must not supply a digest.
    v_payload_sha256 := pg_catalog.encode(
        extensions.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Serialize requests using the same key so concurrent retries cannot both create a record.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_idempotency_key, 0)
    );
    select * into v_existing
      from public.nema_measurement_idempotency
     where idempotency_key = p_idempotency_key;
    if found then
        if pg_catalog.lower(v_existing.payload_sha256) <> v_payload_sha256 then
            raise exception 'idempotency key reused with a different payload' using errcode = '23505';
        end if;
        return pg_catalog.jsonb_build_object(
            'decision', 'replay',
            'measurement_id', v_existing.measurement_id,
            'payload_sha256', v_existing.payload_sha256,
            'audit_created', false
        );
    end if;

    insert into public.nema_indicator_measurements (
        measurement_id, indicator_id, definition_version, reporting_period_start,
        reporting_period_end, reporting_timezone, status, value, unit, numerator,
        denominator, exclusions, source_refs, evidence_refs, calculation_method,
        reviewer_id, verified_at, caveats
    ) values (
        p_measurement_id, p_record->>'indicator_id', p_record->>'definition_version',
        (p_record->>'reporting_period_start')::date, (p_record->>'reporting_period_end')::date,
        p_record->>'reporting_timezone', 'measured', v_value, p_record->>'unit',
        v_numerator, v_denominator,
        coalesce(p_record->'exclusions', '[]'::jsonb),
        p_record->'source_refs', coalesce(p_record->'evidence_refs', '[]'::jsonb),
        p_record->>'calculation_method', null, null, coalesce(p_record->'caveats', '[]'::jsonb)
    );

    insert into public.nema_measurement_idempotency (
        idempotency_key, payload_sha256, measurement_id
    ) values (p_idempotency_key, v_payload_sha256, p_measurement_id);

    insert into public.nema_measurement_audit (
        audit_id, measurement_id, actor_id, actor_role, action, idempotency_key, payload_sha256
    ) values (
        p_measurement_id || ':submitted', p_measurement_id, p_actor_id, p_actor_role,
        'measurement_submitted', p_idempotency_key, v_payload_sha256
    );

    return pg_catalog.jsonb_build_object(
        'decision', 'new',
        'measurement_id', p_measurement_id,
        'payload_sha256', v_payload_sha256,
        'audit_created', true
    );
end;
$function$;

revoke all on table public.nema_measurement_idempotency from anon, authenticated, service_role;
revoke all on table public.nema_measurement_audit from anon, authenticated, service_role;
revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;

-- The function owner has only the table rights the RPC needs. RLS remains enabled;
-- policies below are scoped only to this non-login role. No direct client policies exist.
grant usage on schema public to nema_measurement_writer;
grant usage on schema extensions to nema_measurement_writer;
grant select, insert on table public.nema_indicator_measurements to nema_measurement_writer;
grant select, insert on table public.nema_measurement_idempotency to nema_measurement_writer;
grant insert on table public.nema_measurement_audit to nema_measurement_writer;

drop policy if exists nema_measurement_writer_access on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_select on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_insert on public.nema_indicator_measurements;
create policy nema_measurement_writer_select on public.nema_indicator_measurements
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_indicator_measurements
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_select on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_idempotency;
create policy nema_measurement_writer_select on public.nema_measurement_idempotency
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_measurement_idempotency
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_audit;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_audit;
create policy nema_measurement_writer_insert on public.nema_measurement_audit
    for insert to nema_measurement_writer with check (true);

grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;
grant execute on function extensions.digest(bytea, text) to nema_measurement_writer;
grant select on table public.nema_measurement_idempotency to service_role;
grant select on table public.nema_measurement_audit to service_role;

revoke all on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    from public, anon, authenticated, service_role;

-- PostgreSQL requires the target owner to have CREATE on the containing schema
-- during ALTER FUNCTION OWNER. Grant it only for this ownership transfer, then
-- immediately revoke it so the SECURITY DEFINER owner cannot create schema objects.
grant create on schema public to nema_measurement_writer;
alter function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    owner to nema_measurement_writer;
revoke create on schema public from nema_measurement_writer;

grant execute on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    to service_role;

revoke all on function public.reject_nema_measurement_audit_mutation()
    from public, anon, authenticated, service_role;

commit;

-- REQUIRED before staging approval:
-- * Verify pgcrypto is installed in schema extensions before applying this migration.
-- * Validate database-computed digest parity and replay behavior on the target PostgreSQL version.
-- * Test concurrent duplicate requests, conflict, injected rollback, and unique-key collision.
-- * Verify function owner is nema_measurement_writer (NOLOGIN, NOINHERIT, no BYPASSRLS).
-- * Verify writer-role table grants and command-specific SELECT/INSERT RLS policies match this migration.
-- * Confirm RLS/grants and fixed search_path; verify no anon/authenticated execution.
-- * This RPC does not authenticate p_actor_id/p_actor_role; API must derive these from OIDC/session.
-- * Evidence bytes and reviewer independence require separate authenticated workflows.
        and split_part(object_key, '/', 2) = substr(split_part(object_key, '/', 3), 1, 2)
        and split_part(object_key, '/', 3) = pg_catalog.lower(sha256)
    ),
    constraint nema_evidence_id_nonblank check (length(pg_catalog.btrim(evidence_id)) > 0),
    constraint nema_evidence_actor_nonblank check (length(pg_catalog.btrim(registered_by)) > 0)
);

create table if not exists public.nema_measurement_audit (
    audit_id text primary key,
    measurement_id text not null
        references public.nema_indicator_measurements(measurement_id) on delete restrict,
    actor_id text not null,
    actor_role text not null,
    action text not null check (action = 'measurement_submitted'),
    idempotency_key text not null
        references public.nema_measurement_idempotency(idempotency_key) on delete restrict,
    payload_sha256 text not null check (payload_sha256 ~ '^[a-fA-F0-9]{64}$'),
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_measurement_audit_actor_nonblank check (length(pg_catalog.btrim(actor_id)) > 0)
);

create index if not exists idx_nema_measurement_audit_measurement_created
    on public.nema_measurement_audit (measurement_id, created_at, audit_id);

alter table public.nema_measurement_idempotency enable row level security;
alter table public.nema_measurement_audit enable row level security;

create or replace function public.reject_nema_measurement_audit_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
begin
    raise exception 'NEMA measurement audit events are append-only';
end;
$function$;

drop trigger if exists nema_measurement_audit_no_update on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_update
before update on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

drop trigger if exists nema_measurement_audit_no_delete on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_delete
before delete on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

create or replace function public.submit_nema_indicator_measurement(
    p_measurement_id text,
    p_idempotency_key text,
    p_actor_id text,
    p_actor_role text,
    p_record jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_existing public.nema_measurement_idempotency%rowtype;
    v_value numeric;
    v_numerator numeric;
    v_denominator numeric;
    v_decision text;
    v_payload_sha256 text;
begin
    if p_measurement_id is null or length(pg_catalog.btrim(p_measurement_id)) = 0
       or length(pg_catalog.btrim(p_measurement_id)) > 256 then
        raise exception 'invalid measurement id' using errcode = '22023';
    end if;
    if p_idempotency_key is null or length(pg_catalog.btrim(p_idempotency_key)) = 0
       or length(pg_catalog.btrim(p_idempotency_key)) > 256 then
        raise exception 'invalid idempotency key' using errcode = '22023';
    end if;
    if p_actor_id is null or length(pg_catalog.btrim(p_actor_id)) = 0
       or length(pg_catalog.btrim(p_actor_id)) > 256 then
        raise exception 'invalid trusted actor id' using errcode = '22023';
    end if;
    -- NULL must be rejected explicitly: SQL three-valued logic makes `NULL NOT IN (...)` NULL, not TRUE.
    if p_actor_role is null or p_actor_role not in ('submitter', 'coordinator', 'admin') then
        raise exception 'actor role is not allowed to submit measurements' using errcode = '42501';
    end if;
    if p_record is null or pg_catalog.jsonb_typeof(p_record) <> 'object' then
        raise exception 'measurement record must be a JSON object' using errcode = '22023';
    end if;
    if p_record->>'status' is distinct from 'measured' then
        raise exception 'submission status must be measured; verification is a separate review action'
            using errcode = '22023';
    end if;
    if p_record->>'indicator_id' is null or length(pg_catalog.btrim(p_record->>'indicator_id')) = 0
       or p_record->>'definition_version' is null
       or length(pg_catalog.btrim(p_record->>'definition_version')) = 0
       or p_record->>'reporting_timezone' is null
       or length(pg_catalog.btrim(p_record->>'reporting_timezone')) = 0
       or p_record->>'unit' is null
       or length(pg_catalog.btrim(p_record->>'unit')) = 0
       or p_record->>'calculation_method' is null
       or length(pg_catalog.btrim(p_record->>'calculation_method')) = 0
       or p_record->>'reporting_period_start' is null
       or p_record->>'reporting_period_end' is null then
        raise exception 'required measurement fields are missing' using errcode = '22023';
    end if;
    -- IS DISTINCT FROM rejects SQL NULL as well as JSON values of the wrong type.
    -- Keep array length in a separate branch so it is never evaluated on a non-array.
    if pg_catalog.jsonb_typeof(p_record->'source_refs') is distinct from 'array' then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'source_refs') = 0 then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
         where pg_catalog.jsonb_typeof(source_ref.item) is distinct from 'string'
            or length(pg_catalog.btrim(source_ref.item #>> '{}')) = 0
    ) then
        raise exception 'source_refs entries must be non-empty strings' using errcode = '22023';
    end if;
    if (
        select count(*) <> count(distinct source_ref.item #>> '{}')
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
    ) then
        raise exception 'source_refs entries must be unique' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_typeof(p_record->'evidence_refs') is distinct from 'array' then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'evidence_refs') = 0 then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'evidence_refs') as evidence_ref(item)
         where pg_catalog.jsonb_typeof(evidence_ref.item) is distinct from 'object'
            or pg_catalog.jsonb_typeof(evidence_ref.item->'reference') is distinct from 'string'
            or length(pg_catalog.btrim(evidence_ref.item->>'reference')) = 0
            or pg_catalog.jsonb_typeof(evidence_ref.item->'sha256') is distinct from 'string'
            or (evidence_ref.item->>'sha256') !~ '^[A-Fa-f0-9]{64}$'
    ) then
        raise exception 'evidence_refs require a reference and a valid SHA-256 digest' using errcode = '22023';
    end if;
    if p_record ? 'exclusions' and pg_catalog.jsonb_typeof(p_record->'exclusions') is distinct from 'array' then
        raise exception 'exclusions must be an array' using errcode = '22023';
    end if;
    if p_record ? 'caveats' and pg_catalog.jsonb_typeof(p_record->'caveats') is distinct from 'array' then
        raise exception 'caveats must be an array' using errcode = '22023';
    end if;

    begin
        v_value := (p_record->>'value')::numeric;
        if p_record ? 'numerator' then v_numerator := (p_record->>'numerator')::numeric; end if;
        if p_record ? 'denominator' then v_denominator := (p_record->>'denominator')::numeric; end if;
    exception when others then
        raise exception 'value, numerator, or denominator is not numeric' using errcode = '22023';
    end;
    if v_value is null or v_value < 0 or v_value = 'NaN'::numeric
       or v_value = 'Infinity'::numeric or v_value = '-Infinity'::numeric then
        raise exception 'value must be a finite non-negative number' using errcode = '22023';
    end if;
    if v_numerator is not null and (v_numerator < 0 or v_numerator = 'NaN'::numeric
       or v_numerator = 'Infinity'::numeric or v_numerator = '-Infinity'::numeric) then
        raise exception 'numerator must be finite and non-negative' using errcode = '22023';
    end if;
    if v_denominator is not null and (v_denominator <= 0 or v_denominator = 'NaN'::numeric
       or v_denominator = 'Infinity'::numeric or v_denominator = '-Infinity'::numeric) then
        raise exception 'denominator must be finite and positive' using errcode = '22023';
    end if;
    if v_numerator is not null and v_denominator is not null and v_numerator > v_denominator then
        raise exception 'numerator cannot exceed denominator' using errcode = '22023';
    end if;
    begin
        if (p_record->>'reporting_period_start')::date > (p_record->>'reporting_period_end')::date then
            raise exception 'reporting period end precedes start' using errcode = '22023';
        end if;
    exception when sqlstate '22023' then
        raise;
    when others then
        raise exception 'reporting period dates must be valid ISO dates' using errcode = '22023';
    end;

    -- Compute the digest inside PostgreSQL from the actual database payload. jsonb::text has
    -- deterministic key ordering and formatting within PostgreSQL; the API must not supply a digest.
    v_payload_sha256 := pg_catalog.encode(
        extensions.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Serialize requests using the same key so concurrent retries cannot both create a record.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_idempotency_key, 0)
    );
    select * into v_existing
      from public.nema_measurement_idempotency
     where idempotency_key = p_idempotency_key;
    if found then
        if pg_catalog.lower(v_existing.payload_sha256) <> v_payload_sha256 then
            raise exception 'idempotency key reused with a different payload' using errcode = '23505';
        end if;
        return pg_catalog.jsonb_build_object(
            'decision', 'replay',
            'measurement_id', v_existing.measurement_id,
            'payload_sha256', v_existing.payload_sha256,
            'audit_created', false
        );
    end if;

    insert into public.nema_indicator_measurements (
        measurement_id, indicator_id, definition_version, reporting_period_start,
        reporting_period_end, reporting_timezone, status, value, unit, numerator,
        denominator, exclusions, source_refs, evidence_refs, calculation_method,
        reviewer_id, verified_at, caveats
    ) values (
        p_measurement_id, p_record->>'indicator_id', p_record->>'definition_version',
        (p_record->>'reporting_period_start')::date, (p_record->>'reporting_period_end')::date,
        p_record->>'reporting_timezone', 'measured', v_value, p_record->>'unit',
        v_numerator, v_denominator,
        coalesce(p_record->'exclusions', '[]'::jsonb),
        p_record->'source_refs', coalesce(p_record->'evidence_refs', '[]'::jsonb),
        p_record->>'calculation_method', null, null, coalesce(p_record->'caveats', '[]'::jsonb)
    );

    insert into public.nema_measurement_idempotency (
        idempotency_key, payload_sha256, measurement_id
    ) values (p_idempotency_key, v_payload_sha256, p_measurement_id);

    insert into public.nema_measurement_audit (
        audit_id, measurement_id, actor_id, actor_role, action, idempotency_key, payload_sha256
    ) values (
        p_measurement_id || ':submitted', p_measurement_id, p_actor_id, p_actor_role,
        'measurement_submitted', p_idempotency_key, v_payload_sha256
    );

    return pg_catalog.jsonb_build_object(
        'decision', 'new',
        'measurement_id', p_measurement_id,
        'payload_sha256', v_payload_sha256,
        'audit_created', true
    );
end;
$function$;

revoke all on table public.nema_measurement_idempotency from anon, authenticated, service_role;
revoke all on table public.nema_measurement_audit from anon, authenticated, service_role;
revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;

-- The function owner has only the table rights the RPC needs. RLS remains enabled;
-- policies below are scoped only to this non-login role. No direct client policies exist.
grant usage on schema public to nema_measurement_writer;
grant usage on schema extensions to nema_measurement_writer;
grant select, insert on table public.nema_indicator_measurements to nema_measurement_writer;
grant select, insert on table public.nema_measurement_idempotency to nema_measurement_writer;
grant insert on table public.nema_measurement_audit to nema_measurement_writer;

drop policy if exists nema_measurement_writer_access on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_select on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_insert on public.nema_indicator_measurements;
create policy nema_measurement_writer_select on public.nema_indicator_measurements
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_indicator_measurements
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_select on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_idempotency;
create policy nema_measurement_writer_select on public.nema_measurement_idempotency
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_measurement_idempotency
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_audit;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_audit;
create policy nema_measurement_writer_insert on public.nema_measurement_audit
    for insert to nema_measurement_writer with check (true);

grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;
grant execute on function extensions.digest(bytea, text) to nema_measurement_writer;
grant select on table public.nema_measurement_idempotency to service_role;
grant select on table public.nema_measurement_audit to service_role;

revoke all on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    from public, anon, authenticated, service_role;

-- PostgreSQL requires the target owner to have CREATE on the containing schema
-- during ALTER FUNCTION OWNER. Grant it only for this ownership transfer, then
-- immediately revoke it so the SECURITY DEFINER owner cannot create schema objects.
grant create on schema public to nema_measurement_writer;
alter function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    owner to nema_measurement_writer;
revoke create on schema public from nema_measurement_writer;

grant execute on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    to service_role;

revoke all on function public.reject_nema_measurement_audit_mutation()
    from public, anon, authenticated, service_role;

commit;

-- REQUIRED before staging approval:
-- * Verify pgcrypto is installed in schema extensions before applying this migration.
-- * Validate database-computed digest parity and replay behavior on the target PostgreSQL version.
-- * Test concurrent duplicate requests, conflict, injected rollback, and unique-key collision.
-- * Verify function owner is nema_measurement_writer (NOLOGIN, NOINHERIT, no BYPASSRLS).
-- * Verify writer-role table grants and command-specific SELECT/INSERT RLS policies match this migration.
-- * Confirm RLS/grants and fixed search_path; verify no anon/authenticated execution.
-- * This RPC does not authenticate p_actor_id/p_actor_role; API must derive these from OIDC/session.
-- * Evidence bytes and reviewer independence require separate authenticated workflows.
            or (evidence_ref.item->>'reference') !~ '^[a-z0-9][a-z0-9._-]{1,62}/sha256/[0-9a-f]{2}/[0-9a-f]{64}
        raise exception 'evidence_refs require a reference and a valid SHA-256 digest' using errcode = '22023';
    end if;
    if p_record ? 'exclusions' and pg_catalog.jsonb_typeof(p_record->'exclusions') is distinct from 'array' then
        raise exception 'exclusions must be an array' using errcode = '22023';
    end if;
    if p_record ? 'caveats' and pg_catalog.jsonb_typeof(p_record->'caveats') is distinct from 'array' then
        raise exception 'caveats must be an array' using errcode = '22023';
    end if;

    begin
        v_value := (p_record->>'value')::numeric;
        if p_record ? 'numerator' then v_numerator := (p_record->>'numerator')::numeric; end if;
        if p_record ? 'denominator' then v_denominator := (p_record->>'denominator')::numeric; end if;
    exception when others then
        raise exception 'value, numerator, or denominator is not numeric' using errcode = '22023';
    end;
    if v_value is null or v_value < 0 or v_value = 'NaN'::numeric
       or v_value = 'Infinity'::numeric or v_value = '-Infinity'::numeric then
        raise exception 'value must be a finite non-negative number' using errcode = '22023';
    end if;
    if v_numerator is not null and (v_numerator < 0 or v_numerator = 'NaN'::numeric
       or v_numerator = 'Infinity'::numeric or v_numerator = '-Infinity'::numeric) then
        raise exception 'numerator must be finite and non-negative' using errcode = '22023';
    end if;
    if v_denominator is not null and (v_denominator <= 0 or v_denominator = 'NaN'::numeric
       or v_denominator = 'Infinity'::numeric or v_denominator = '-Infinity'::numeric) then
        raise exception 'denominator must be finite and positive' using errcode = '22023';
    end if;
    if v_numerator is not null and v_denominator is not null and v_numerator > v_denominator then
        raise exception 'numerator cannot exceed denominator' using errcode = '22023';
    end if;
    begin
        if (p_record->>'reporting_period_start')::date > (p_record->>'reporting_period_end')::date then
            raise exception 'reporting period end precedes start' using errcode = '22023';
        end if;
    exception when sqlstate '22023' then
        raise;
    when others then
        raise exception 'reporting period dates must be valid ISO dates' using errcode = '22023';
    end;

    -- Compute the digest inside PostgreSQL from the actual database payload. jsonb::text has
    -- deterministic key ordering and formatting within PostgreSQL; the API must not supply a digest.
    v_payload_sha256 := pg_catalog.encode(
        extensions.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Serialize requests using the same key so concurrent retries cannot both create a record.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_idempotency_key, 0)
    );
    select * into v_existing
      from public.nema_measurement_idempotency
     where idempotency_key = p_idempotency_key;
    if found then
        if pg_catalog.lower(v_existing.payload_sha256) <> v_payload_sha256 then
            raise exception 'idempotency key reused with a different payload' using errcode = '23505';
        end if;
        return pg_catalog.jsonb_build_object(
            'decision', 'replay',
            'measurement_id', v_existing.measurement_id,
            'payload_sha256', v_existing.payload_sha256,
            'audit_created', false
        );
    end if;

    insert into public.nema_indicator_measurements (
        measurement_id, indicator_id, definition_version, reporting_period_start,
        reporting_period_end, reporting_timezone, status, value, unit, numerator,
        denominator, exclusions, source_refs, evidence_refs, calculation_method,
        reviewer_id, verified_at, caveats
    ) values (
        p_measurement_id, p_record->>'indicator_id', p_record->>'definition_version',
        (p_record->>'reporting_period_start')::date, (p_record->>'reporting_period_end')::date,
        p_record->>'reporting_timezone', 'measured', v_value, p_record->>'unit',
        v_numerator, v_denominator,
        coalesce(p_record->'exclusions', '[]'::jsonb),
        p_record->'source_refs', coalesce(p_record->'evidence_refs', '[]'::jsonb),
        p_record->>'calculation_method', null, null, coalesce(p_record->'caveats', '[]'::jsonb)
    );

    insert into public.nema_measurement_idempotency (
        idempotency_key, payload_sha256, measurement_id
    ) values (p_idempotency_key, v_payload_sha256, p_measurement_id);

    insert into public.nema_measurement_audit (
        audit_id, measurement_id, actor_id, actor_role, action, idempotency_key, payload_sha256
    ) values (
        p_measurement_id || ':submitted', p_measurement_id, p_actor_id, p_actor_role,
        'measurement_submitted', p_idempotency_key, v_payload_sha256
    );

    return pg_catalog.jsonb_build_object(
        'decision', 'new',
        'measurement_id', p_measurement_id,
        'payload_sha256', v_payload_sha256,
        'audit_created', true
    );
end;
$function$;

revoke all on table public.nema_measurement_idempotency from anon, authenticated, service_role;
revoke all on table public.nema_measurement_audit from anon, authenticated, service_role;
revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;

-- The function owner has only the table rights the RPC needs. RLS remains enabled;
-- policies below are scoped only to this non-login role. No direct client policies exist.
grant usage on schema public to nema_measurement_writer;
grant usage on schema extensions to nema_measurement_writer;
grant select, insert on table public.nema_indicator_measurements to nema_measurement_writer;
grant select, insert on table public.nema_measurement_idempotency to nema_measurement_writer;
grant insert on table public.nema_measurement_audit to nema_measurement_writer;

drop policy if exists nema_measurement_writer_access on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_select on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_insert on public.nema_indicator_measurements;
create policy nema_measurement_writer_select on public.nema_indicator_measurements
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_indicator_measurements
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_select on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_idempotency;
create policy nema_measurement_writer_select on public.nema_measurement_idempotency
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_measurement_idempotency
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_audit;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_audit;
create policy nema_measurement_writer_insert on public.nema_measurement_audit
    for insert to nema_measurement_writer with check (true);

grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;
grant execute on function extensions.digest(bytea, text) to nema_measurement_writer;
grant select on table public.nema_measurement_idempotency to service_role;
grant select on table public.nema_measurement_audit to service_role;

revoke all on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    from public, anon, authenticated, service_role;

-- PostgreSQL requires the target owner to have CREATE on the containing schema
-- during ALTER FUNCTION OWNER. Grant it only for this ownership transfer, then
-- immediately revoke it so the SECURITY DEFINER owner cannot create schema objects.
grant create on schema public to nema_measurement_writer;
alter function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    owner to nema_measurement_writer;
revoke create on schema public from nema_measurement_writer;

grant execute on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    to service_role;

revoke all on function public.reject_nema_measurement_audit_mutation()
    from public, anon, authenticated, service_role;

commit;

-- REQUIRED before staging approval:
-- * Verify pgcrypto is installed in schema extensions before applying this migration.
-- * Validate database-computed digest parity and replay behavior on the target PostgreSQL version.
-- * Test concurrent duplicate requests, conflict, injected rollback, and unique-key collision.
-- * Verify function owner is nema_measurement_writer (NOLOGIN, NOINHERIT, no BYPASSRLS).
-- * Verify writer-role table grants and command-specific SELECT/INSERT RLS policies match this migration.
-- * Confirm RLS/grants and fixed search_path; verify no anon/authenticated execution.
-- * This RPC does not authenticate p_actor_id/p_actor_role; API must derive these from OIDC/session.
-- * Evidence bytes and reviewer independence require separate authenticated workflows.),
    object_key text not null,
    sha256 text not null check (sha256 ~ '^[a-fA-F0-9]{64}
    measurement_id text not null
        references public.nema_indicator_measurements(measurement_id) on delete restrict,
    actor_id text not null,
    actor_role text not null,
    action text not null check (action = 'measurement_submitted'),
    idempotency_key text not null
        references public.nema_measurement_idempotency(idempotency_key) on delete restrict,
    payload_sha256 text not null check (payload_sha256 ~ '^[a-fA-F0-9]{64}$'),
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_measurement_audit_actor_nonblank check (length(pg_catalog.btrim(actor_id)) > 0)
);

create index if not exists idx_nema_measurement_audit_measurement_created
    on public.nema_measurement_audit (measurement_id, created_at, audit_id);

alter table public.nema_measurement_idempotency enable row level security;
alter table public.nema_measurement_audit enable row level security;

create or replace function public.reject_nema_measurement_audit_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
begin
    raise exception 'NEMA measurement audit events are append-only';
end;
$function$;

drop trigger if exists nema_measurement_audit_no_update on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_update
before update on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

drop trigger if exists nema_measurement_audit_no_delete on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_delete
before delete on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

create or replace function public.submit_nema_indicator_measurement(
    p_measurement_id text,
    p_idempotency_key text,
    p_actor_id text,
    p_actor_role text,
    p_record jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_existing public.nema_measurement_idempotency%rowtype;
    v_value numeric;
    v_numerator numeric;
    v_denominator numeric;
    v_decision text;
    v_payload_sha256 text;
begin
    if p_measurement_id is null or length(pg_catalog.btrim(p_measurement_id)) = 0
       or length(pg_catalog.btrim(p_measurement_id)) > 256 then
        raise exception 'invalid measurement id' using errcode = '22023';
    end if;
    if p_idempotency_key is null or length(pg_catalog.btrim(p_idempotency_key)) = 0
       or length(pg_catalog.btrim(p_idempotency_key)) > 256 then
        raise exception 'invalid idempotency key' using errcode = '22023';
    end if;
    if p_actor_id is null or length(pg_catalog.btrim(p_actor_id)) = 0
       or length(pg_catalog.btrim(p_actor_id)) > 256 then
        raise exception 'invalid trusted actor id' using errcode = '22023';
    end if;
    -- NULL must be rejected explicitly: SQL three-valued logic makes `NULL NOT IN (...)` NULL, not TRUE.
    if p_actor_role is null or p_actor_role not in ('submitter', 'coordinator', 'admin') then
        raise exception 'actor role is not allowed to submit measurements' using errcode = '42501';
    end if;
    if p_record is null or pg_catalog.jsonb_typeof(p_record) <> 'object' then
        raise exception 'measurement record must be a JSON object' using errcode = '22023';
    end if;
    if p_record->>'status' is distinct from 'measured' then
        raise exception 'submission status must be measured; verification is a separate review action'
            using errcode = '22023';
    end if;
    if p_record->>'indicator_id' is null or length(pg_catalog.btrim(p_record->>'indicator_id')) = 0
       or p_record->>'definition_version' is null
       or length(pg_catalog.btrim(p_record->>'definition_version')) = 0
       or p_record->>'reporting_timezone' is null
       or length(pg_catalog.btrim(p_record->>'reporting_timezone')) = 0
       or p_record->>'unit' is null
       or length(pg_catalog.btrim(p_record->>'unit')) = 0
       or p_record->>'calculation_method' is null
       or length(pg_catalog.btrim(p_record->>'calculation_method')) = 0
       or p_record->>'reporting_period_start' is null
       or p_record->>'reporting_period_end' is null then
        raise exception 'required measurement fields are missing' using errcode = '22023';
    end if;
    -- IS DISTINCT FROM rejects SQL NULL as well as JSON values of the wrong type.
    -- Keep array length in a separate branch so it is never evaluated on a non-array.
    if pg_catalog.jsonb_typeof(p_record->'source_refs') is distinct from 'array' then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'source_refs') = 0 then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
         where pg_catalog.jsonb_typeof(source_ref.item) is distinct from 'string'
            or length(pg_catalog.btrim(source_ref.item #>> '{}')) = 0
    ) then
        raise exception 'source_refs entries must be non-empty strings' using errcode = '22023';
    end if;
    if (
        select count(*) <> count(distinct source_ref.item #>> '{}')
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
    ) then
        raise exception 'source_refs entries must be unique' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_typeof(p_record->'evidence_refs') is distinct from 'array' then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'evidence_refs') = 0 then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'evidence_refs') as evidence_ref(item)
         where pg_catalog.jsonb_typeof(evidence_ref.item) is distinct from 'object'
            or pg_catalog.jsonb_typeof(evidence_ref.item->'reference') is distinct from 'string'
            or length(pg_catalog.btrim(evidence_ref.item->>'reference')) = 0
            or pg_catalog.jsonb_typeof(evidence_ref.item->'sha256') is distinct from 'string'
            or (evidence_ref.item->>'sha256') !~ '^[A-Fa-f0-9]{64}$'
    ) then
        raise exception 'evidence_refs require a reference and a valid SHA-256 digest' using errcode = '22023';
    end if;
    if p_record ? 'exclusions' and pg_catalog.jsonb_typeof(p_record->'exclusions') is distinct from 'array' then
        raise exception 'exclusions must be an array' using errcode = '22023';
    end if;
    if p_record ? 'caveats' and pg_catalog.jsonb_typeof(p_record->'caveats') is distinct from 'array' then
        raise exception 'caveats must be an array' using errcode = '22023';
    end if;

    begin
        v_value := (p_record->>'value')::numeric;
        if p_record ? 'numerator' then v_numerator := (p_record->>'numerator')::numeric; end if;
        if p_record ? 'denominator' then v_denominator := (p_record->>'denominator')::numeric; end if;
    exception when others then
        raise exception 'value, numerator, or denominator is not numeric' using errcode = '22023';
    end;
    if v_value is null or v_value < 0 or v_value = 'NaN'::numeric
       or v_value = 'Infinity'::numeric or v_value = '-Infinity'::numeric then
        raise exception 'value must be a finite non-negative number' using errcode = '22023';
    end if;
    if v_numerator is not null and (v_numerator < 0 or v_numerator = 'NaN'::numeric
       or v_numerator = 'Infinity'::numeric or v_numerator = '-Infinity'::numeric) then
        raise exception 'numerator must be finite and non-negative' using errcode = '22023';
    end if;
    if v_denominator is not null and (v_denominator <= 0 or v_denominator = 'NaN'::numeric
       or v_denominator = 'Infinity'::numeric or v_denominator = '-Infinity'::numeric) then
        raise exception 'denominator must be finite and positive' using errcode = '22023';
    end if;
    if v_numerator is not null and v_denominator is not null and v_numerator > v_denominator then
        raise exception 'numerator cannot exceed denominator' using errcode = '22023';
    end if;
    begin
        if (p_record->>'reporting_period_start')::date > (p_record->>'reporting_period_end')::date then
            raise exception 'reporting period end precedes start' using errcode = '22023';
        end if;
    exception when sqlstate '22023' then
        raise;
    when others then
        raise exception 'reporting period dates must be valid ISO dates' using errcode = '22023';
    end;

    -- Compute the digest inside PostgreSQL from the actual database payload. jsonb::text has
    -- deterministic key ordering and formatting within PostgreSQL; the API must not supply a digest.
    v_payload_sha256 := pg_catalog.encode(
        extensions.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Serialize requests using the same key so concurrent retries cannot both create a record.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_idempotency_key, 0)
    );
    select * into v_existing
      from public.nema_measurement_idempotency
     where idempotency_key = p_idempotency_key;
    if found then
        if pg_catalog.lower(v_existing.payload_sha256) <> v_payload_sha256 then
            raise exception 'idempotency key reused with a different payload' using errcode = '23505';
        end if;
        return pg_catalog.jsonb_build_object(
            'decision', 'replay',
            'measurement_id', v_existing.measurement_id,
            'payload_sha256', v_existing.payload_sha256,
            'audit_created', false
        );
    end if;

    insert into public.nema_indicator_measurements (
        measurement_id, indicator_id, definition_version, reporting_period_start,
        reporting_period_end, reporting_timezone, status, value, unit, numerator,
        denominator, exclusions, source_refs, evidence_refs, calculation_method,
        reviewer_id, verified_at, caveats
    ) values (
        p_measurement_id, p_record->>'indicator_id', p_record->>'definition_version',
        (p_record->>'reporting_period_start')::date, (p_record->>'reporting_period_end')::date,
        p_record->>'reporting_timezone', 'measured', v_value, p_record->>'unit',
        v_numerator, v_denominator,
        coalesce(p_record->'exclusions', '[]'::jsonb),
        p_record->'source_refs', coalesce(p_record->'evidence_refs', '[]'::jsonb),
        p_record->>'calculation_method', null, null, coalesce(p_record->'caveats', '[]'::jsonb)
    );

    insert into public.nema_measurement_idempotency (
        idempotency_key, payload_sha256, measurement_id
    ) values (p_idempotency_key, v_payload_sha256, p_measurement_id);

    insert into public.nema_measurement_audit (
        audit_id, measurement_id, actor_id, actor_role, action, idempotency_key, payload_sha256
    ) values (
        p_measurement_id || ':submitted', p_measurement_id, p_actor_id, p_actor_role,
        'measurement_submitted', p_idempotency_key, v_payload_sha256
    );

    return pg_catalog.jsonb_build_object(
        'decision', 'new',
        'measurement_id', p_measurement_id,
        'payload_sha256', v_payload_sha256,
        'audit_created', true
    );
end;
$function$;

revoke all on table public.nema_measurement_idempotency from anon, authenticated, service_role;
revoke all on table public.nema_measurement_audit from anon, authenticated, service_role;
revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;

-- The function owner has only the table rights the RPC needs. RLS remains enabled;
-- policies below are scoped only to this non-login role. No direct client policies exist.
grant usage on schema public to nema_measurement_writer;
grant usage on schema extensions to nema_measurement_writer;
grant select, insert on table public.nema_indicator_measurements to nema_measurement_writer;
grant select, insert on table public.nema_measurement_idempotency to nema_measurement_writer;
grant insert on table public.nema_measurement_audit to nema_measurement_writer;

drop policy if exists nema_measurement_writer_access on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_select on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_insert on public.nema_indicator_measurements;
create policy nema_measurement_writer_select on public.nema_indicator_measurements
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_indicator_measurements
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_select on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_idempotency;
create policy nema_measurement_writer_select on public.nema_measurement_idempotency
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_measurement_idempotency
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_audit;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_audit;
create policy nema_measurement_writer_insert on public.nema_measurement_audit
    for insert to nema_measurement_writer with check (true);

grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;
grant execute on function extensions.digest(bytea, text) to nema_measurement_writer;
grant select on table public.nema_measurement_idempotency to service_role;
grant select on table public.nema_measurement_audit to service_role;

revoke all on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    from public, anon, authenticated, service_role;

-- PostgreSQL requires the target owner to have CREATE on the containing schema
-- during ALTER FUNCTION OWNER. Grant it only for this ownership transfer, then
-- immediately revoke it so the SECURITY DEFINER owner cannot create schema objects.
grant create on schema public to nema_measurement_writer;
alter function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    owner to nema_measurement_writer;
revoke create on schema public from nema_measurement_writer;

grant execute on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    to service_role;

revoke all on function public.reject_nema_measurement_audit_mutation()
    from public, anon, authenticated, service_role;

commit;

-- REQUIRED before staging approval:
-- * Verify pgcrypto is installed in schema extensions before applying this migration.
-- * Validate database-computed digest parity and replay behavior on the target PostgreSQL version.
-- * Test concurrent duplicate requests, conflict, injected rollback, and unique-key collision.
-- * Verify function owner is nema_measurement_writer (NOLOGIN, NOINHERIT, no BYPASSRLS).
-- * Verify writer-role table grants and command-specific SELECT/INSERT RLS policies match this migration.
-- * Confirm RLS/grants and fixed search_path; verify no anon/authenticated execution.
-- * This RPC does not authenticate p_actor_id/p_actor_role; API must derive these from OIDC/session.
-- * Evidence bytes and reviewer independence require separate authenticated workflows.),
    registered_by text not null,
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_evidence_bucket_object_unique unique (bucket_name, object_key),
    constraint nema_evidence_object_key_shape check (
        object_key ~ '^sha256/[0-9a-f]{2}/[0-9a-f]{64}
    measurement_id text not null
        references public.nema_indicator_measurements(measurement_id) on delete restrict,
    actor_id text not null,
    actor_role text not null,
    action text not null check (action = 'measurement_submitted'),
    idempotency_key text not null
        references public.nema_measurement_idempotency(idempotency_key) on delete restrict,
    payload_sha256 text not null check (payload_sha256 ~ '^[a-fA-F0-9]{64}$'),
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_measurement_audit_actor_nonblank check (length(pg_catalog.btrim(actor_id)) > 0)
);

create index if not exists idx_nema_measurement_audit_measurement_created
    on public.nema_measurement_audit (measurement_id, created_at, audit_id);

alter table public.nema_measurement_idempotency enable row level security;
alter table public.nema_measurement_audit enable row level security;

create or replace function public.reject_nema_measurement_audit_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
begin
    raise exception 'NEMA measurement audit events are append-only';
end;
$function$;

drop trigger if exists nema_measurement_audit_no_update on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_update
before update on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

drop trigger if exists nema_measurement_audit_no_delete on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_delete
before delete on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

create or replace function public.submit_nema_indicator_measurement(
    p_measurement_id text,
    p_idempotency_key text,
    p_actor_id text,
    p_actor_role text,
    p_record jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_existing public.nema_measurement_idempotency%rowtype;
    v_value numeric;
    v_numerator numeric;
    v_denominator numeric;
    v_decision text;
    v_payload_sha256 text;
begin
    if p_measurement_id is null or length(pg_catalog.btrim(p_measurement_id)) = 0
       or length(pg_catalog.btrim(p_measurement_id)) > 256 then
        raise exception 'invalid measurement id' using errcode = '22023';
    end if;
    if p_idempotency_key is null or length(pg_catalog.btrim(p_idempotency_key)) = 0
       or length(pg_catalog.btrim(p_idempotency_key)) > 256 then
        raise exception 'invalid idempotency key' using errcode = '22023';
    end if;
    if p_actor_id is null or length(pg_catalog.btrim(p_actor_id)) = 0
       or length(pg_catalog.btrim(p_actor_id)) > 256 then
        raise exception 'invalid trusted actor id' using errcode = '22023';
    end if;
    -- NULL must be rejected explicitly: SQL three-valued logic makes `NULL NOT IN (...)` NULL, not TRUE.
    if p_actor_role is null or p_actor_role not in ('submitter', 'coordinator', 'admin') then
        raise exception 'actor role is not allowed to submit measurements' using errcode = '42501';
    end if;
    if p_record is null or pg_catalog.jsonb_typeof(p_record) <> 'object' then
        raise exception 'measurement record must be a JSON object' using errcode = '22023';
    end if;
    if p_record->>'status' is distinct from 'measured' then
        raise exception 'submission status must be measured; verification is a separate review action'
            using errcode = '22023';
    end if;
    if p_record->>'indicator_id' is null or length(pg_catalog.btrim(p_record->>'indicator_id')) = 0
       or p_record->>'definition_version' is null
       or length(pg_catalog.btrim(p_record->>'definition_version')) = 0
       or p_record->>'reporting_timezone' is null
       or length(pg_catalog.btrim(p_record->>'reporting_timezone')) = 0
       or p_record->>'unit' is null
       or length(pg_catalog.btrim(p_record->>'unit')) = 0
       or p_record->>'calculation_method' is null
       or length(pg_catalog.btrim(p_record->>'calculation_method')) = 0
       or p_record->>'reporting_period_start' is null
       or p_record->>'reporting_period_end' is null then
        raise exception 'required measurement fields are missing' using errcode = '22023';
    end if;
    -- IS DISTINCT FROM rejects SQL NULL as well as JSON values of the wrong type.
    -- Keep array length in a separate branch so it is never evaluated on a non-array.
    if pg_catalog.jsonb_typeof(p_record->'source_refs') is distinct from 'array' then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'source_refs') = 0 then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
         where pg_catalog.jsonb_typeof(source_ref.item) is distinct from 'string'
            or length(pg_catalog.btrim(source_ref.item #>> '{}')) = 0
    ) then
        raise exception 'source_refs entries must be non-empty strings' using errcode = '22023';
    end if;
    if (
        select count(*) <> count(distinct source_ref.item #>> '{}')
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
    ) then
        raise exception 'source_refs entries must be unique' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_typeof(p_record->'evidence_refs') is distinct from 'array' then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'evidence_refs') = 0 then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'evidence_refs') as evidence_ref(item)
         where pg_catalog.jsonb_typeof(evidence_ref.item) is distinct from 'object'
            or pg_catalog.jsonb_typeof(evidence_ref.item->'reference') is distinct from 'string'
            or length(pg_catalog.btrim(evidence_ref.item->>'reference')) = 0
            or pg_catalog.jsonb_typeof(evidence_ref.item->'sha256') is distinct from 'string'
            or (evidence_ref.item->>'sha256') !~ '^[A-Fa-f0-9]{64}$'
    ) then
        raise exception 'evidence_refs require a reference and a valid SHA-256 digest' using errcode = '22023';
    end if;
    if p_record ? 'exclusions' and pg_catalog.jsonb_typeof(p_record->'exclusions') is distinct from 'array' then
        raise exception 'exclusions must be an array' using errcode = '22023';
    end if;
    if p_record ? 'caveats' and pg_catalog.jsonb_typeof(p_record->'caveats') is distinct from 'array' then
        raise exception 'caveats must be an array' using errcode = '22023';
    end if;

    begin
        v_value := (p_record->>'value')::numeric;
        if p_record ? 'numerator' then v_numerator := (p_record->>'numerator')::numeric; end if;
        if p_record ? 'denominator' then v_denominator := (p_record->>'denominator')::numeric; end if;
    exception when others then
        raise exception 'value, numerator, or denominator is not numeric' using errcode = '22023';
    end;
    if v_value is null or v_value < 0 or v_value = 'NaN'::numeric
       or v_value = 'Infinity'::numeric or v_value = '-Infinity'::numeric then
        raise exception 'value must be a finite non-negative number' using errcode = '22023';
    end if;
    if v_numerator is not null and (v_numerator < 0 or v_numerator = 'NaN'::numeric
       or v_numerator = 'Infinity'::numeric or v_numerator = '-Infinity'::numeric) then
        raise exception 'numerator must be finite and non-negative' using errcode = '22023';
    end if;
    if v_denominator is not null and (v_denominator <= 0 or v_denominator = 'NaN'::numeric
       or v_denominator = 'Infinity'::numeric or v_denominator = '-Infinity'::numeric) then
        raise exception 'denominator must be finite and positive' using errcode = '22023';
    end if;
    if v_numerator is not null and v_denominator is not null and v_numerator > v_denominator then
        raise exception 'numerator cannot exceed denominator' using errcode = '22023';
    end if;
    begin
        if (p_record->>'reporting_period_start')::date > (p_record->>'reporting_period_end')::date then
            raise exception 'reporting period end precedes start' using errcode = '22023';
        end if;
    exception when sqlstate '22023' then
        raise;
    when others then
        raise exception 'reporting period dates must be valid ISO dates' using errcode = '22023';
    end;

    -- Compute the digest inside PostgreSQL from the actual database payload. jsonb::text has
    -- deterministic key ordering and formatting within PostgreSQL; the API must not supply a digest.
    v_payload_sha256 := pg_catalog.encode(
        extensions.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Serialize requests using the same key so concurrent retries cannot both create a record.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_idempotency_key, 0)
    );
    select * into v_existing
      from public.nema_measurement_idempotency
     where idempotency_key = p_idempotency_key;
    if found then
        if pg_catalog.lower(v_existing.payload_sha256) <> v_payload_sha256 then
            raise exception 'idempotency key reused with a different payload' using errcode = '23505';
        end if;
        return pg_catalog.jsonb_build_object(
            'decision', 'replay',
            'measurement_id', v_existing.measurement_id,
            'payload_sha256', v_existing.payload_sha256,
            'audit_created', false
        );
    end if;

    insert into public.nema_indicator_measurements (
        measurement_id, indicator_id, definition_version, reporting_period_start,
        reporting_period_end, reporting_timezone, status, value, unit, numerator,
        denominator, exclusions, source_refs, evidence_refs, calculation_method,
        reviewer_id, verified_at, caveats
    ) values (
        p_measurement_id, p_record->>'indicator_id', p_record->>'definition_version',
        (p_record->>'reporting_period_start')::date, (p_record->>'reporting_period_end')::date,
        p_record->>'reporting_timezone', 'measured', v_value, p_record->>'unit',
        v_numerator, v_denominator,
        coalesce(p_record->'exclusions', '[]'::jsonb),
        p_record->'source_refs', coalesce(p_record->'evidence_refs', '[]'::jsonb),
        p_record->>'calculation_method', null, null, coalesce(p_record->'caveats', '[]'::jsonb)
    );

    insert into public.nema_measurement_idempotency (
        idempotency_key, payload_sha256, measurement_id
    ) values (p_idempotency_key, v_payload_sha256, p_measurement_id);

    insert into public.nema_measurement_audit (
        audit_id, measurement_id, actor_id, actor_role, action, idempotency_key, payload_sha256
    ) values (
        p_measurement_id || ':submitted', p_measurement_id, p_actor_id, p_actor_role,
        'measurement_submitted', p_idempotency_key, v_payload_sha256
    );

    return pg_catalog.jsonb_build_object(
        'decision', 'new',
        'measurement_id', p_measurement_id,
        'payload_sha256', v_payload_sha256,
        'audit_created', true
    );
end;
$function$;

revoke all on table public.nema_measurement_idempotency from anon, authenticated, service_role;
revoke all on table public.nema_measurement_audit from anon, authenticated, service_role;
revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;

-- The function owner has only the table rights the RPC needs. RLS remains enabled;
-- policies below are scoped only to this non-login role. No direct client policies exist.
grant usage on schema public to nema_measurement_writer;
grant usage on schema extensions to nema_measurement_writer;
grant select, insert on table public.nema_indicator_measurements to nema_measurement_writer;
grant select, insert on table public.nema_measurement_idempotency to nema_measurement_writer;
grant insert on table public.nema_measurement_audit to nema_measurement_writer;

drop policy if exists nema_measurement_writer_access on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_select on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_insert on public.nema_indicator_measurements;
create policy nema_measurement_writer_select on public.nema_indicator_measurements
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_indicator_measurements
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_select on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_idempotency;
create policy nema_measurement_writer_select on public.nema_measurement_idempotency
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_measurement_idempotency
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_audit;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_audit;
create policy nema_measurement_writer_insert on public.nema_measurement_audit
    for insert to nema_measurement_writer with check (true);

grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;
grant execute on function extensions.digest(bytea, text) to nema_measurement_writer;
grant select on table public.nema_measurement_idempotency to service_role;
grant select on table public.nema_measurement_audit to service_role;

revoke all on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    from public, anon, authenticated, service_role;

-- PostgreSQL requires the target owner to have CREATE on the containing schema
-- during ALTER FUNCTION OWNER. Grant it only for this ownership transfer, then
-- immediately revoke it so the SECURITY DEFINER owner cannot create schema objects.
grant create on schema public to nema_measurement_writer;
alter function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    owner to nema_measurement_writer;
revoke create on schema public from nema_measurement_writer;

grant execute on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    to service_role;

revoke all on function public.reject_nema_measurement_audit_mutation()
    from public, anon, authenticated, service_role;

commit;

-- REQUIRED before staging approval:
-- * Verify pgcrypto is installed in schema extensions before applying this migration.
-- * Validate database-computed digest parity and replay behavior on the target PostgreSQL version.
-- * Test concurrent duplicate requests, conflict, injected rollback, and unique-key collision.
-- * Verify function owner is nema_measurement_writer (NOLOGIN, NOINHERIT, no BYPASSRLS).
-- * Verify writer-role table grants and command-specific SELECT/INSERT RLS policies match this migration.
-- * Confirm RLS/grants and fixed search_path; verify no anon/authenticated execution.
-- * This RPC does not authenticate p_actor_id/p_actor_role; API must derive these from OIDC/session.
-- * Evidence bytes and reviewer independence require separate authenticated workflows.
        and split_part(object_key, '/', 2) = substr(split_part(object_key, '/', 3), 1, 2)
        and split_part(object_key, '/', 3) = pg_catalog.lower(sha256)
    ),
    constraint nema_evidence_id_nonblank check (length(pg_catalog.btrim(evidence_id)) > 0),
    constraint nema_evidence_actor_nonblank check (length(pg_catalog.btrim(registered_by)) > 0)
);

create table if not exists public.nema_measurement_audit (
    audit_id text primary key,
    measurement_id text not null
        references public.nema_indicator_measurements(measurement_id) on delete restrict,
    actor_id text not null,
    actor_role text not null,
    action text not null check (action = 'measurement_submitted'),
    idempotency_key text not null
        references public.nema_measurement_idempotency(idempotency_key) on delete restrict,
    payload_sha256 text not null check (payload_sha256 ~ '^[a-fA-F0-9]{64}$'),
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_measurement_audit_actor_nonblank check (length(pg_catalog.btrim(actor_id)) > 0)
);

create index if not exists idx_nema_measurement_audit_measurement_created
    on public.nema_measurement_audit (measurement_id, created_at, audit_id);

alter table public.nema_measurement_idempotency enable row level security;
alter table public.nema_measurement_audit enable row level security;

create or replace function public.reject_nema_measurement_audit_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
begin
    raise exception 'NEMA measurement audit events are append-only';
end;
$function$;

drop trigger if exists nema_measurement_audit_no_update on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_update
before update on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

drop trigger if exists nema_measurement_audit_no_delete on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_delete
before delete on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

create or replace function public.submit_nema_indicator_measurement(
    p_measurement_id text,
    p_idempotency_key text,
    p_actor_id text,
    p_actor_role text,
    p_record jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_existing public.nema_measurement_idempotency%rowtype;
    v_value numeric;
    v_numerator numeric;
    v_denominator numeric;
    v_decision text;
    v_payload_sha256 text;
begin
    if p_measurement_id is null or length(pg_catalog.btrim(p_measurement_id)) = 0
       or length(pg_catalog.btrim(p_measurement_id)) > 256 then
        raise exception 'invalid measurement id' using errcode = '22023';
    end if;
    if p_idempotency_key is null or length(pg_catalog.btrim(p_idempotency_key)) = 0
       or length(pg_catalog.btrim(p_idempotency_key)) > 256 then
        raise exception 'invalid idempotency key' using errcode = '22023';
    end if;
    if p_actor_id is null or length(pg_catalog.btrim(p_actor_id)) = 0
       or length(pg_catalog.btrim(p_actor_id)) > 256 then
        raise exception 'invalid trusted actor id' using errcode = '22023';
    end if;
    -- NULL must be rejected explicitly: SQL three-valued logic makes `NULL NOT IN (...)` NULL, not TRUE.
    if p_actor_role is null or p_actor_role not in ('submitter', 'coordinator', 'admin') then
        raise exception 'actor role is not allowed to submit measurements' using errcode = '42501';
    end if;
    if p_record is null or pg_catalog.jsonb_typeof(p_record) <> 'object' then
        raise exception 'measurement record must be a JSON object' using errcode = '22023';
    end if;
    if p_record->>'status' is distinct from 'measured' then
        raise exception 'submission status must be measured; verification is a separate review action'
            using errcode = '22023';
    end if;
    if p_record->>'indicator_id' is null or length(pg_catalog.btrim(p_record->>'indicator_id')) = 0
       or p_record->>'definition_version' is null
       or length(pg_catalog.btrim(p_record->>'definition_version')) = 0
       or p_record->>'reporting_timezone' is null
       or length(pg_catalog.btrim(p_record->>'reporting_timezone')) = 0
       or p_record->>'unit' is null
       or length(pg_catalog.btrim(p_record->>'unit')) = 0
       or p_record->>'calculation_method' is null
       or length(pg_catalog.btrim(p_record->>'calculation_method')) = 0
       or p_record->>'reporting_period_start' is null
       or p_record->>'reporting_period_end' is null then
        raise exception 'required measurement fields are missing' using errcode = '22023';
    end if;
    -- IS DISTINCT FROM rejects SQL NULL as well as JSON values of the wrong type.
    -- Keep array length in a separate branch so it is never evaluated on a non-array.
    if pg_catalog.jsonb_typeof(p_record->'source_refs') is distinct from 'array' then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'source_refs') = 0 then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
         where pg_catalog.jsonb_typeof(source_ref.item) is distinct from 'string'
            or length(pg_catalog.btrim(source_ref.item #>> '{}')) = 0
    ) then
        raise exception 'source_refs entries must be non-empty strings' using errcode = '22023';
    end if;
    if (
        select count(*) <> count(distinct source_ref.item #>> '{}')
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
    ) then
        raise exception 'source_refs entries must be unique' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_typeof(p_record->'evidence_refs') is distinct from 'array' then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'evidence_refs') = 0 then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'evidence_refs') as evidence_ref(item)
         where pg_catalog.jsonb_typeof(evidence_ref.item) is distinct from 'object'
            or pg_catalog.jsonb_typeof(evidence_ref.item->'reference') is distinct from 'string'
            or length(pg_catalog.btrim(evidence_ref.item->>'reference')) = 0
            or pg_catalog.jsonb_typeof(evidence_ref.item->'sha256') is distinct from 'string'
            or (evidence_ref.item->>'sha256') !~ '^[A-Fa-f0-9]{64}$'
    ) then
        raise exception 'evidence_refs require a reference and a valid SHA-256 digest' using errcode = '22023';
    end if;
    if p_record ? 'exclusions' and pg_catalog.jsonb_typeof(p_record->'exclusions') is distinct from 'array' then
        raise exception 'exclusions must be an array' using errcode = '22023';
    end if;
    if p_record ? 'caveats' and pg_catalog.jsonb_typeof(p_record->'caveats') is distinct from 'array' then
        raise exception 'caveats must be an array' using errcode = '22023';
    end if;

    begin
        v_value := (p_record->>'value')::numeric;
        if p_record ? 'numerator' then v_numerator := (p_record->>'numerator')::numeric; end if;
        if p_record ? 'denominator' then v_denominator := (p_record->>'denominator')::numeric; end if;
    exception when others then
        raise exception 'value, numerator, or denominator is not numeric' using errcode = '22023';
    end;
    if v_value is null or v_value < 0 or v_value = 'NaN'::numeric
       or v_value = 'Infinity'::numeric or v_value = '-Infinity'::numeric then
        raise exception 'value must be a finite non-negative number' using errcode = '22023';
    end if;
    if v_numerator is not null and (v_numerator < 0 or v_numerator = 'NaN'::numeric
       or v_numerator = 'Infinity'::numeric or v_numerator = '-Infinity'::numeric) then
        raise exception 'numerator must be finite and non-negative' using errcode = '22023';
    end if;
    if v_denominator is not null and (v_denominator <= 0 or v_denominator = 'NaN'::numeric
       or v_denominator = 'Infinity'::numeric or v_denominator = '-Infinity'::numeric) then
        raise exception 'denominator must be finite and positive' using errcode = '22023';
    end if;
    if v_numerator is not null and v_denominator is not null and v_numerator > v_denominator then
        raise exception 'numerator cannot exceed denominator' using errcode = '22023';
    end if;
    begin
        if (p_record->>'reporting_period_start')::date > (p_record->>'reporting_period_end')::date then
            raise exception 'reporting period end precedes start' using errcode = '22023';
        end if;
    exception when sqlstate '22023' then
        raise;
    when others then
        raise exception 'reporting period dates must be valid ISO dates' using errcode = '22023';
    end;

    -- Compute the digest inside PostgreSQL from the actual database payload. jsonb::text has
    -- deterministic key ordering and formatting within PostgreSQL; the API must not supply a digest.
    v_payload_sha256 := pg_catalog.encode(
        extensions.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Serialize requests using the same key so concurrent retries cannot both create a record.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_idempotency_key, 0)
    );
    select * into v_existing
      from public.nema_measurement_idempotency
     where idempotency_key = p_idempotency_key;
    if found then
        if pg_catalog.lower(v_existing.payload_sha256) <> v_payload_sha256 then
            raise exception 'idempotency key reused with a different payload' using errcode = '23505';
        end if;
        return pg_catalog.jsonb_build_object(
            'decision', 'replay',
            'measurement_id', v_existing.measurement_id,
            'payload_sha256', v_existing.payload_sha256,
            'audit_created', false
        );
    end if;

    insert into public.nema_indicator_measurements (
        measurement_id, indicator_id, definition_version, reporting_period_start,
        reporting_period_end, reporting_timezone, status, value, unit, numerator,
        denominator, exclusions, source_refs, evidence_refs, calculation_method,
        reviewer_id, verified_at, caveats
    ) values (
        p_measurement_id, p_record->>'indicator_id', p_record->>'definition_version',
        (p_record->>'reporting_period_start')::date, (p_record->>'reporting_period_end')::date,
        p_record->>'reporting_timezone', 'measured', v_value, p_record->>'unit',
        v_numerator, v_denominator,
        coalesce(p_record->'exclusions', '[]'::jsonb),
        p_record->'source_refs', coalesce(p_record->'evidence_refs', '[]'::jsonb),
        p_record->>'calculation_method', null, null, coalesce(p_record->'caveats', '[]'::jsonb)
    );

    insert into public.nema_measurement_idempotency (
        idempotency_key, payload_sha256, measurement_id
    ) values (p_idempotency_key, v_payload_sha256, p_measurement_id);

    insert into public.nema_measurement_audit (
        audit_id, measurement_id, actor_id, actor_role, action, idempotency_key, payload_sha256
    ) values (
        p_measurement_id || ':submitted', p_measurement_id, p_actor_id, p_actor_role,
        'measurement_submitted', p_idempotency_key, v_payload_sha256
    );

    return pg_catalog.jsonb_build_object(
        'decision', 'new',
        'measurement_id', p_measurement_id,
        'payload_sha256', v_payload_sha256,
        'audit_created', true
    );
end;
$function$;

revoke all on table public.nema_measurement_idempotency from anon, authenticated, service_role;
revoke all on table public.nema_measurement_audit from anon, authenticated, service_role;
revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;

-- The function owner has only the table rights the RPC needs. RLS remains enabled;
-- policies below are scoped only to this non-login role. No direct client policies exist.
grant usage on schema public to nema_measurement_writer;
grant usage on schema extensions to nema_measurement_writer;
grant select, insert on table public.nema_indicator_measurements to nema_measurement_writer;
grant select, insert on table public.nema_measurement_idempotency to nema_measurement_writer;
grant insert on table public.nema_measurement_audit to nema_measurement_writer;

drop policy if exists nema_measurement_writer_access on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_select on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_insert on public.nema_indicator_measurements;
create policy nema_measurement_writer_select on public.nema_indicator_measurements
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_indicator_measurements
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_select on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_idempotency;
create policy nema_measurement_writer_select on public.nema_measurement_idempotency
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_measurement_idempotency
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_audit;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_audit;
create policy nema_measurement_writer_insert on public.nema_measurement_audit
    for insert to nema_measurement_writer with check (true);

grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;
grant execute on function extensions.digest(bytea, text) to nema_measurement_writer;
grant select on table public.nema_measurement_idempotency to service_role;
grant select on table public.nema_measurement_audit to service_role;

revoke all on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    from public, anon, authenticated, service_role;

-- PostgreSQL requires the target owner to have CREATE on the containing schema
-- during ALTER FUNCTION OWNER. Grant it only for this ownership transfer, then
-- immediately revoke it so the SECURITY DEFINER owner cannot create schema objects.
grant create on schema public to nema_measurement_writer;
alter function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    owner to nema_measurement_writer;
revoke create on schema public from nema_measurement_writer;

grant execute on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    to service_role;

revoke all on function public.reject_nema_measurement_audit_mutation()
    from public, anon, authenticated, service_role;

commit;

-- REQUIRED before staging approval:
-- * Verify pgcrypto is installed in schema extensions before applying this migration.
-- * Validate database-computed digest parity and replay behavior on the target PostgreSQL version.
-- * Test concurrent duplicate requests, conflict, injected rollback, and unique-key collision.
-- * Verify function owner is nema_measurement_writer (NOLOGIN, NOINHERIT, no BYPASSRLS).
-- * Verify writer-role table grants and command-specific SELECT/INSERT RLS policies match this migration.
-- * Confirm RLS/grants and fixed search_path; verify no anon/authenticated execution.
-- * This RPC does not authenticate p_actor_id/p_actor_role; API must derive these from OIDC/session.
-- * Evidence bytes and reviewer independence require separate authenticated workflows.
            or split_part(evidence_ref.item->>'reference', '/', 3) <> substr(pg_catalog.lower(evidence_ref.item->>'sha256'), 1, 2)
            or split_part(evidence_ref.item->>'reference', '/', 4) <> pg_catalog.lower(evidence_ref.item->>'sha256')
    ) then
        raise exception 'evidence_refs require a reference and a valid SHA-256 digest' using errcode = '22023';
    end if;
    if p_record ? 'exclusions' and pg_catalog.jsonb_typeof(p_record->'exclusions') is distinct from 'array' then
        raise exception 'exclusions must be an array' using errcode = '22023';
    end if;
    if p_record ? 'caveats' and pg_catalog.jsonb_typeof(p_record->'caveats') is distinct from 'array' then
        raise exception 'caveats must be an array' using errcode = '22023';
    end if;

    begin
        v_value := (p_record->>'value')::numeric;
        if p_record ? 'numerator' then v_numerator := (p_record->>'numerator')::numeric; end if;
        if p_record ? 'denominator' then v_denominator := (p_record->>'denominator')::numeric; end if;
    exception when others then
        raise exception 'value, numerator, or denominator is not numeric' using errcode = '22023';
    end;
    if v_value is null or v_value < 0 or v_value = 'NaN'::numeric
       or v_value = 'Infinity'::numeric or v_value = '-Infinity'::numeric then
        raise exception 'value must be a finite non-negative number' using errcode = '22023';
    end if;
    if v_numerator is not null and (v_numerator < 0 or v_numerator = 'NaN'::numeric
       or v_numerator = 'Infinity'::numeric or v_numerator = '-Infinity'::numeric) then
        raise exception 'numerator must be finite and non-negative' using errcode = '22023';
    end if;
    if v_denominator is not null and (v_denominator <= 0 or v_denominator = 'NaN'::numeric
       or v_denominator = 'Infinity'::numeric or v_denominator = '-Infinity'::numeric) then
        raise exception 'denominator must be finite and positive' using errcode = '22023';
    end if;
    if v_numerator is not null and v_denominator is not null and v_numerator > v_denominator then
        raise exception 'numerator cannot exceed denominator' using errcode = '22023';
    end if;
    begin
        if (p_record->>'reporting_period_start')::date > (p_record->>'reporting_period_end')::date then
            raise exception 'reporting period end precedes start' using errcode = '22023';
        end if;
    exception when sqlstate '22023' then
        raise;
    when others then
        raise exception 'reporting period dates must be valid ISO dates' using errcode = '22023';
    end;

    -- Compute the digest inside PostgreSQL from the actual database payload. jsonb::text has
    -- deterministic key ordering and formatting within PostgreSQL; the API must not supply a digest.
    v_payload_sha256 := pg_catalog.encode(
        extensions.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Serialize requests using the same key so concurrent retries cannot both create a record.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_idempotency_key, 0)
    );
    select * into v_existing
      from public.nema_measurement_idempotency
     where idempotency_key = p_idempotency_key;
    if found then
        if pg_catalog.lower(v_existing.payload_sha256) <> v_payload_sha256 then
            raise exception 'idempotency key reused with a different payload' using errcode = '23505';
        end if;
        return pg_catalog.jsonb_build_object(
            'decision', 'replay',
            'measurement_id', v_existing.measurement_id,
            'payload_sha256', v_existing.payload_sha256,
            'audit_created', false
        );
    end if;

    insert into public.nema_indicator_measurements (
        measurement_id, indicator_id, definition_version, reporting_period_start,
        reporting_period_end, reporting_timezone, status, value, unit, numerator,
        denominator, exclusions, source_refs, evidence_refs, calculation_method,
        reviewer_id, verified_at, caveats
    ) values (
        p_measurement_id, p_record->>'indicator_id', p_record->>'definition_version',
        (p_record->>'reporting_period_start')::date, (p_record->>'reporting_period_end')::date,
        p_record->>'reporting_timezone', 'measured', v_value, p_record->>'unit',
        v_numerator, v_denominator,
        coalesce(p_record->'exclusions', '[]'::jsonb),
        p_record->'source_refs', coalesce(p_record->'evidence_refs', '[]'::jsonb),
        p_record->>'calculation_method', null, null, coalesce(p_record->'caveats', '[]'::jsonb)
    );

    insert into public.nema_measurement_idempotency (
        idempotency_key, payload_sha256, measurement_id
    ) values (p_idempotency_key, v_payload_sha256, p_measurement_id);

    insert into public.nema_measurement_audit (
        audit_id, measurement_id, actor_id, actor_role, action, idempotency_key, payload_sha256
    ) values (
        p_measurement_id || ':submitted', p_measurement_id, p_actor_id, p_actor_role,
        'measurement_submitted', p_idempotency_key, v_payload_sha256
    );

    return pg_catalog.jsonb_build_object(
        'decision', 'new',
        'measurement_id', p_measurement_id,
        'payload_sha256', v_payload_sha256,
        'audit_created', true
    );
end;
$function$;

revoke all on table public.nema_measurement_idempotency from anon, authenticated, service_role;
revoke all on table public.nema_measurement_audit from anon, authenticated, service_role;
revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;

-- The function owner has only the table rights the RPC needs. RLS remains enabled;
-- policies below are scoped only to this non-login role. No direct client policies exist.
grant usage on schema public to nema_measurement_writer;
grant usage on schema extensions to nema_measurement_writer;
grant select, insert on table public.nema_indicator_measurements to nema_measurement_writer;
grant select, insert on table public.nema_measurement_idempotency to nema_measurement_writer;
grant insert on table public.nema_measurement_audit to nema_measurement_writer;

drop policy if exists nema_measurement_writer_access on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_select on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_insert on public.nema_indicator_measurements;
create policy nema_measurement_writer_select on public.nema_indicator_measurements
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_indicator_measurements
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_select on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_idempotency;
create policy nema_measurement_writer_select on public.nema_measurement_idempotency
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_measurement_idempotency
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_audit;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_audit;
create policy nema_measurement_writer_insert on public.nema_measurement_audit
    for insert to nema_measurement_writer with check (true);

grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;
grant execute on function extensions.digest(bytea, text) to nema_measurement_writer;
grant select on table public.nema_measurement_idempotency to service_role;
grant select on table public.nema_measurement_audit to service_role;

revoke all on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    from public, anon, authenticated, service_role;

-- PostgreSQL requires the target owner to have CREATE on the containing schema
-- during ALTER FUNCTION OWNER. Grant it only for this ownership transfer, then
-- immediately revoke it so the SECURITY DEFINER owner cannot create schema objects.
grant create on schema public to nema_measurement_writer;
alter function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    owner to nema_measurement_writer;
revoke create on schema public from nema_measurement_writer;

grant execute on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    to service_role;

revoke all on function public.reject_nema_measurement_audit_mutation()
    from public, anon, authenticated, service_role;

commit;

-- REQUIRED before staging approval:
-- * Verify pgcrypto is installed in schema extensions before applying this migration.
-- * Validate database-computed digest parity and replay behavior on the target PostgreSQL version.
-- * Test concurrent duplicate requests, conflict, injected rollback, and unique-key collision.
-- * Verify function owner is nema_measurement_writer (NOLOGIN, NOINHERIT, no BYPASSRLS).
-- * Verify writer-role table grants and command-specific SELECT/INSERT RLS policies match this migration.
-- * Confirm RLS/grants and fixed search_path; verify no anon/authenticated execution.
-- * This RPC does not authenticate p_actor_id/p_actor_role; API must derive these from OIDC/session.
-- * Evidence bytes and reviewer independence require separate authenticated workflows.),
    object_key text not null,
    sha256 text not null check (sha256 ~ '^[a-fA-F0-9]{64}
    measurement_id text not null
        references public.nema_indicator_measurements(measurement_id) on delete restrict,
    actor_id text not null,
    actor_role text not null,
    action text not null check (action = 'measurement_submitted'),
    idempotency_key text not null
        references public.nema_measurement_idempotency(idempotency_key) on delete restrict,
    payload_sha256 text not null check (payload_sha256 ~ '^[a-fA-F0-9]{64}$'),
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_measurement_audit_actor_nonblank check (length(pg_catalog.btrim(actor_id)) > 0)
);

create index if not exists idx_nema_measurement_audit_measurement_created
    on public.nema_measurement_audit (measurement_id, created_at, audit_id);

alter table public.nema_measurement_idempotency enable row level security;
alter table public.nema_measurement_audit enable row level security;

create or replace function public.reject_nema_measurement_audit_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
begin
    raise exception 'NEMA measurement audit events are append-only';
end;
$function$;

drop trigger if exists nema_measurement_audit_no_update on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_update
before update on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

drop trigger if exists nema_measurement_audit_no_delete on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_delete
before delete on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

create or replace function public.submit_nema_indicator_measurement(
    p_measurement_id text,
    p_idempotency_key text,
    p_actor_id text,
    p_actor_role text,
    p_record jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_existing public.nema_measurement_idempotency%rowtype;
    v_value numeric;
    v_numerator numeric;
    v_denominator numeric;
    v_decision text;
    v_payload_sha256 text;
begin
    if p_measurement_id is null or length(pg_catalog.btrim(p_measurement_id)) = 0
       or length(pg_catalog.btrim(p_measurement_id)) > 256 then
        raise exception 'invalid measurement id' using errcode = '22023';
    end if;
    if p_idempotency_key is null or length(pg_catalog.btrim(p_idempotency_key)) = 0
       or length(pg_catalog.btrim(p_idempotency_key)) > 256 then
        raise exception 'invalid idempotency key' using errcode = '22023';
    end if;
    if p_actor_id is null or length(pg_catalog.btrim(p_actor_id)) = 0
       or length(pg_catalog.btrim(p_actor_id)) > 256 then
        raise exception 'invalid trusted actor id' using errcode = '22023';
    end if;
    -- NULL must be rejected explicitly: SQL three-valued logic makes `NULL NOT IN (...)` NULL, not TRUE.
    if p_actor_role is null or p_actor_role not in ('submitter', 'coordinator', 'admin') then
        raise exception 'actor role is not allowed to submit measurements' using errcode = '42501';
    end if;
    if p_record is null or pg_catalog.jsonb_typeof(p_record) <> 'object' then
        raise exception 'measurement record must be a JSON object' using errcode = '22023';
    end if;
    if p_record->>'status' is distinct from 'measured' then
        raise exception 'submission status must be measured; verification is a separate review action'
            using errcode = '22023';
    end if;
    if p_record->>'indicator_id' is null or length(pg_catalog.btrim(p_record->>'indicator_id')) = 0
       or p_record->>'definition_version' is null
       or length(pg_catalog.btrim(p_record->>'definition_version')) = 0
       or p_record->>'reporting_timezone' is null
       or length(pg_catalog.btrim(p_record->>'reporting_timezone')) = 0
       or p_record->>'unit' is null
       or length(pg_catalog.btrim(p_record->>'unit')) = 0
       or p_record->>'calculation_method' is null
       or length(pg_catalog.btrim(p_record->>'calculation_method')) = 0
       or p_record->>'reporting_period_start' is null
       or p_record->>'reporting_period_end' is null then
        raise exception 'required measurement fields are missing' using errcode = '22023';
    end if;
    -- IS DISTINCT FROM rejects SQL NULL as well as JSON values of the wrong type.
    -- Keep array length in a separate branch so it is never evaluated on a non-array.
    if pg_catalog.jsonb_typeof(p_record->'source_refs') is distinct from 'array' then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'source_refs') = 0 then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
         where pg_catalog.jsonb_typeof(source_ref.item) is distinct from 'string'
            or length(pg_catalog.btrim(source_ref.item #>> '{}')) = 0
    ) then
        raise exception 'source_refs entries must be non-empty strings' using errcode = '22023';
    end if;
    if (
        select count(*) <> count(distinct source_ref.item #>> '{}')
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
    ) then
        raise exception 'source_refs entries must be unique' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_typeof(p_record->'evidence_refs') is distinct from 'array' then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'evidence_refs') = 0 then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'evidence_refs') as evidence_ref(item)
         where pg_catalog.jsonb_typeof(evidence_ref.item) is distinct from 'object'
            or pg_catalog.jsonb_typeof(evidence_ref.item->'reference') is distinct from 'string'
            or length(pg_catalog.btrim(evidence_ref.item->>'reference')) = 0
            or pg_catalog.jsonb_typeof(evidence_ref.item->'sha256') is distinct from 'string'
            or (evidence_ref.item->>'sha256') !~ '^[A-Fa-f0-9]{64}$'
    ) then
        raise exception 'evidence_refs require a reference and a valid SHA-256 digest' using errcode = '22023';
    end if;
    if p_record ? 'exclusions' and pg_catalog.jsonb_typeof(p_record->'exclusions') is distinct from 'array' then
        raise exception 'exclusions must be an array' using errcode = '22023';
    end if;
    if p_record ? 'caveats' and pg_catalog.jsonb_typeof(p_record->'caveats') is distinct from 'array' then
        raise exception 'caveats must be an array' using errcode = '22023';
    end if;

    begin
        v_value := (p_record->>'value')::numeric;
        if p_record ? 'numerator' then v_numerator := (p_record->>'numerator')::numeric; end if;
        if p_record ? 'denominator' then v_denominator := (p_record->>'denominator')::numeric; end if;
    exception when others then
        raise exception 'value, numerator, or denominator is not numeric' using errcode = '22023';
    end;
    if v_value is null or v_value < 0 or v_value = 'NaN'::numeric
       or v_value = 'Infinity'::numeric or v_value = '-Infinity'::numeric then
        raise exception 'value must be a finite non-negative number' using errcode = '22023';
    end if;
    if v_numerator is not null and (v_numerator < 0 or v_numerator = 'NaN'::numeric
       or v_numerator = 'Infinity'::numeric or v_numerator = '-Infinity'::numeric) then
        raise exception 'numerator must be finite and non-negative' using errcode = '22023';
    end if;
    if v_denominator is not null and (v_denominator <= 0 or v_denominator = 'NaN'::numeric
       or v_denominator = 'Infinity'::numeric or v_denominator = '-Infinity'::numeric) then
        raise exception 'denominator must be finite and positive' using errcode = '22023';
    end if;
    if v_numerator is not null and v_denominator is not null and v_numerator > v_denominator then
        raise exception 'numerator cannot exceed denominator' using errcode = '22023';
    end if;
    begin
        if (p_record->>'reporting_period_start')::date > (p_record->>'reporting_period_end')::date then
            raise exception 'reporting period end precedes start' using errcode = '22023';
        end if;
    exception when sqlstate '22023' then
        raise;
    when others then
        raise exception 'reporting period dates must be valid ISO dates' using errcode = '22023';
    end;

    -- Compute the digest inside PostgreSQL from the actual database payload. jsonb::text has
    -- deterministic key ordering and formatting within PostgreSQL; the API must not supply a digest.
    v_payload_sha256 := pg_catalog.encode(
        extensions.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Serialize requests using the same key so concurrent retries cannot both create a record.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_idempotency_key, 0)
    );
    select * into v_existing
      from public.nema_measurement_idempotency
     where idempotency_key = p_idempotency_key;
    if found then
        if pg_catalog.lower(v_existing.payload_sha256) <> v_payload_sha256 then
            raise exception 'idempotency key reused with a different payload' using errcode = '23505';
        end if;
        return pg_catalog.jsonb_build_object(
            'decision', 'replay',
            'measurement_id', v_existing.measurement_id,
            'payload_sha256', v_existing.payload_sha256,
            'audit_created', false
        );
    end if;

    insert into public.nema_indicator_measurements (
        measurement_id, indicator_id, definition_version, reporting_period_start,
        reporting_period_end, reporting_timezone, status, value, unit, numerator,
        denominator, exclusions, source_refs, evidence_refs, calculation_method,
        reviewer_id, verified_at, caveats
    ) values (
        p_measurement_id, p_record->>'indicator_id', p_record->>'definition_version',
        (p_record->>'reporting_period_start')::date, (p_record->>'reporting_period_end')::date,
        p_record->>'reporting_timezone', 'measured', v_value, p_record->>'unit',
        v_numerator, v_denominator,
        coalesce(p_record->'exclusions', '[]'::jsonb),
        p_record->'source_refs', coalesce(p_record->'evidence_refs', '[]'::jsonb),
        p_record->>'calculation_method', null, null, coalesce(p_record->'caveats', '[]'::jsonb)
    );

    insert into public.nema_measurement_idempotency (
        idempotency_key, payload_sha256, measurement_id
    ) values (p_idempotency_key, v_payload_sha256, p_measurement_id);

    insert into public.nema_measurement_audit (
        audit_id, measurement_id, actor_id, actor_role, action, idempotency_key, payload_sha256
    ) values (
        p_measurement_id || ':submitted', p_measurement_id, p_actor_id, p_actor_role,
        'measurement_submitted', p_idempotency_key, v_payload_sha256
    );

    return pg_catalog.jsonb_build_object(
        'decision', 'new',
        'measurement_id', p_measurement_id,
        'payload_sha256', v_payload_sha256,
        'audit_created', true
    );
end;
$function$;

revoke all on table public.nema_measurement_idempotency from anon, authenticated, service_role;
revoke all on table public.nema_measurement_audit from anon, authenticated, service_role;
revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;

-- The function owner has only the table rights the RPC needs. RLS remains enabled;
-- policies below are scoped only to this non-login role. No direct client policies exist.
grant usage on schema public to nema_measurement_writer;
grant usage on schema extensions to nema_measurement_writer;
grant select, insert on table public.nema_indicator_measurements to nema_measurement_writer;
grant select, insert on table public.nema_measurement_idempotency to nema_measurement_writer;
grant insert on table public.nema_measurement_audit to nema_measurement_writer;

drop policy if exists nema_measurement_writer_access on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_select on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_insert on public.nema_indicator_measurements;
create policy nema_measurement_writer_select on public.nema_indicator_measurements
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_indicator_measurements
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_select on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_idempotency;
create policy nema_measurement_writer_select on public.nema_measurement_idempotency
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_measurement_idempotency
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_audit;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_audit;
create policy nema_measurement_writer_insert on public.nema_measurement_audit
    for insert to nema_measurement_writer with check (true);

grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;
grant execute on function extensions.digest(bytea, text) to nema_measurement_writer;
grant select on table public.nema_measurement_idempotency to service_role;
grant select on table public.nema_measurement_audit to service_role;

revoke all on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    from public, anon, authenticated, service_role;

-- PostgreSQL requires the target owner to have CREATE on the containing schema
-- during ALTER FUNCTION OWNER. Grant it only for this ownership transfer, then
-- immediately revoke it so the SECURITY DEFINER owner cannot create schema objects.
grant create on schema public to nema_measurement_writer;
alter function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    owner to nema_measurement_writer;
revoke create on schema public from nema_measurement_writer;

grant execute on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    to service_role;

revoke all on function public.reject_nema_measurement_audit_mutation()
    from public, anon, authenticated, service_role;

commit;

-- REQUIRED before staging approval:
-- * Verify pgcrypto is installed in schema extensions before applying this migration.
-- * Validate database-computed digest parity and replay behavior on the target PostgreSQL version.
-- * Test concurrent duplicate requests, conflict, injected rollback, and unique-key collision.
-- * Verify function owner is nema_measurement_writer (NOLOGIN, NOINHERIT, no BYPASSRLS).
-- * Verify writer-role table grants and command-specific SELECT/INSERT RLS policies match this migration.
-- * Confirm RLS/grants and fixed search_path; verify no anon/authenticated execution.
-- * This RPC does not authenticate p_actor_id/p_actor_role; API must derive these from OIDC/session.
-- * Evidence bytes and reviewer independence require separate authenticated workflows.),
    registered_by text not null,
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_evidence_bucket_object_unique unique (bucket_name, object_key),
    constraint nema_evidence_object_key_shape check (
        object_key ~ '^sha256/[0-9a-f]{2}/[0-9a-f]{64}
    measurement_id text not null
        references public.nema_indicator_measurements(measurement_id) on delete restrict,
    actor_id text not null,
    actor_role text not null,
    action text not null check (action = 'measurement_submitted'),
    idempotency_key text not null
        references public.nema_measurement_idempotency(idempotency_key) on delete restrict,
    payload_sha256 text not null check (payload_sha256 ~ '^[a-fA-F0-9]{64}$'),
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_measurement_audit_actor_nonblank check (length(pg_catalog.btrim(actor_id)) > 0)
);

create index if not exists idx_nema_measurement_audit_measurement_created
    on public.nema_measurement_audit (measurement_id, created_at, audit_id);

alter table public.nema_measurement_idempotency enable row level security;
alter table public.nema_measurement_audit enable row level security;

create or replace function public.reject_nema_measurement_audit_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
begin
    raise exception 'NEMA measurement audit events are append-only';
end;
$function$;

drop trigger if exists nema_measurement_audit_no_update on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_update
before update on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

drop trigger if exists nema_measurement_audit_no_delete on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_delete
before delete on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

create or replace function public.submit_nema_indicator_measurement(
    p_measurement_id text,
    p_idempotency_key text,
    p_actor_id text,
    p_actor_role text,
    p_record jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_existing public.nema_measurement_idempotency%rowtype;
    v_value numeric;
    v_numerator numeric;
    v_denominator numeric;
    v_decision text;
    v_payload_sha256 text;
begin
    if p_measurement_id is null or length(pg_catalog.btrim(p_measurement_id)) = 0
       or length(pg_catalog.btrim(p_measurement_id)) > 256 then
        raise exception 'invalid measurement id' using errcode = '22023';
    end if;
    if p_idempotency_key is null or length(pg_catalog.btrim(p_idempotency_key)) = 0
       or length(pg_catalog.btrim(p_idempotency_key)) > 256 then
        raise exception 'invalid idempotency key' using errcode = '22023';
    end if;
    if p_actor_id is null or length(pg_catalog.btrim(p_actor_id)) = 0
       or length(pg_catalog.btrim(p_actor_id)) > 256 then
        raise exception 'invalid trusted actor id' using errcode = '22023';
    end if;
    -- NULL must be rejected explicitly: SQL three-valued logic makes `NULL NOT IN (...)` NULL, not TRUE.
    if p_actor_role is null or p_actor_role not in ('submitter', 'coordinator', 'admin') then
        raise exception 'actor role is not allowed to submit measurements' using errcode = '42501';
    end if;
    if p_record is null or pg_catalog.jsonb_typeof(p_record) <> 'object' then
        raise exception 'measurement record must be a JSON object' using errcode = '22023';
    end if;
    if p_record->>'status' is distinct from 'measured' then
        raise exception 'submission status must be measured; verification is a separate review action'
            using errcode = '22023';
    end if;
    if p_record->>'indicator_id' is null or length(pg_catalog.btrim(p_record->>'indicator_id')) = 0
       or p_record->>'definition_version' is null
       or length(pg_catalog.btrim(p_record->>'definition_version')) = 0
       or p_record->>'reporting_timezone' is null
       or length(pg_catalog.btrim(p_record->>'reporting_timezone')) = 0
       or p_record->>'unit' is null
       or length(pg_catalog.btrim(p_record->>'unit')) = 0
       or p_record->>'calculation_method' is null
       or length(pg_catalog.btrim(p_record->>'calculation_method')) = 0
       or p_record->>'reporting_period_start' is null
       or p_record->>'reporting_period_end' is null then
        raise exception 'required measurement fields are missing' using errcode = '22023';
    end if;
    -- IS DISTINCT FROM rejects SQL NULL as well as JSON values of the wrong type.
    -- Keep array length in a separate branch so it is never evaluated on a non-array.
    if pg_catalog.jsonb_typeof(p_record->'source_refs') is distinct from 'array' then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'source_refs') = 0 then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
         where pg_catalog.jsonb_typeof(source_ref.item) is distinct from 'string'
            or length(pg_catalog.btrim(source_ref.item #>> '{}')) = 0
    ) then
        raise exception 'source_refs entries must be non-empty strings' using errcode = '22023';
    end if;
    if (
        select count(*) <> count(distinct source_ref.item #>> '{}')
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
    ) then
        raise exception 'source_refs entries must be unique' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_typeof(p_record->'evidence_refs') is distinct from 'array' then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'evidence_refs') = 0 then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'evidence_refs') as evidence_ref(item)
         where pg_catalog.jsonb_typeof(evidence_ref.item) is distinct from 'object'
            or pg_catalog.jsonb_typeof(evidence_ref.item->'reference') is distinct from 'string'
            or length(pg_catalog.btrim(evidence_ref.item->>'reference')) = 0
            or pg_catalog.jsonb_typeof(evidence_ref.item->'sha256') is distinct from 'string'
            or (evidence_ref.item->>'sha256') !~ '^[A-Fa-f0-9]{64}$'
    ) then
        raise exception 'evidence_refs require a reference and a valid SHA-256 digest' using errcode = '22023';
    end if;
    if p_record ? 'exclusions' and pg_catalog.jsonb_typeof(p_record->'exclusions') is distinct from 'array' then
        raise exception 'exclusions must be an array' using errcode = '22023';
    end if;
    if p_record ? 'caveats' and pg_catalog.jsonb_typeof(p_record->'caveats') is distinct from 'array' then
        raise exception 'caveats must be an array' using errcode = '22023';
    end if;

    begin
        v_value := (p_record->>'value')::numeric;
        if p_record ? 'numerator' then v_numerator := (p_record->>'numerator')::numeric; end if;
        if p_record ? 'denominator' then v_denominator := (p_record->>'denominator')::numeric; end if;
    exception when others then
        raise exception 'value, numerator, or denominator is not numeric' using errcode = '22023';
    end;
    if v_value is null or v_value < 0 or v_value = 'NaN'::numeric
       or v_value = 'Infinity'::numeric or v_value = '-Infinity'::numeric then
        raise exception 'value must be a finite non-negative number' using errcode = '22023';
    end if;
    if v_numerator is not null and (v_numerator < 0 or v_numerator = 'NaN'::numeric
       or v_numerator = 'Infinity'::numeric or v_numerator = '-Infinity'::numeric) then
        raise exception 'numerator must be finite and non-negative' using errcode = '22023';
    end if;
    if v_denominator is not null and (v_denominator <= 0 or v_denominator = 'NaN'::numeric
       or v_denominator = 'Infinity'::numeric or v_denominator = '-Infinity'::numeric) then
        raise exception 'denominator must be finite and positive' using errcode = '22023';
    end if;
    if v_numerator is not null and v_denominator is not null and v_numerator > v_denominator then
        raise exception 'numerator cannot exceed denominator' using errcode = '22023';
    end if;
    begin
        if (p_record->>'reporting_period_start')::date > (p_record->>'reporting_period_end')::date then
            raise exception 'reporting period end precedes start' using errcode = '22023';
        end if;
    exception when sqlstate '22023' then
        raise;
    when others then
        raise exception 'reporting period dates must be valid ISO dates' using errcode = '22023';
    end;

    -- Compute the digest inside PostgreSQL from the actual database payload. jsonb::text has
    -- deterministic key ordering and formatting within PostgreSQL; the API must not supply a digest.
    v_payload_sha256 := pg_catalog.encode(
        extensions.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Serialize requests using the same key so concurrent retries cannot both create a record.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_idempotency_key, 0)
    );
    select * into v_existing
      from public.nema_measurement_idempotency
     where idempotency_key = p_idempotency_key;
    if found then
        if pg_catalog.lower(v_existing.payload_sha256) <> v_payload_sha256 then
            raise exception 'idempotency key reused with a different payload' using errcode = '23505';
        end if;
        return pg_catalog.jsonb_build_object(
            'decision', 'replay',
            'measurement_id', v_existing.measurement_id,
            'payload_sha256', v_existing.payload_sha256,
            'audit_created', false
        );
    end if;

    insert into public.nema_indicator_measurements (
        measurement_id, indicator_id, definition_version, reporting_period_start,
        reporting_period_end, reporting_timezone, status, value, unit, numerator,
        denominator, exclusions, source_refs, evidence_refs, calculation_method,
        reviewer_id, verified_at, caveats
    ) values (
        p_measurement_id, p_record->>'indicator_id', p_record->>'definition_version',
        (p_record->>'reporting_period_start')::date, (p_record->>'reporting_period_end')::date,
        p_record->>'reporting_timezone', 'measured', v_value, p_record->>'unit',
        v_numerator, v_denominator,
        coalesce(p_record->'exclusions', '[]'::jsonb),
        p_record->'source_refs', coalesce(p_record->'evidence_refs', '[]'::jsonb),
        p_record->>'calculation_method', null, null, coalesce(p_record->'caveats', '[]'::jsonb)
    );

    insert into public.nema_measurement_idempotency (
        idempotency_key, payload_sha256, measurement_id
    ) values (p_idempotency_key, v_payload_sha256, p_measurement_id);

    insert into public.nema_measurement_audit (
        audit_id, measurement_id, actor_id, actor_role, action, idempotency_key, payload_sha256
    ) values (
        p_measurement_id || ':submitted', p_measurement_id, p_actor_id, p_actor_role,
        'measurement_submitted', p_idempotency_key, v_payload_sha256
    );

    return pg_catalog.jsonb_build_object(
        'decision', 'new',
        'measurement_id', p_measurement_id,
        'payload_sha256', v_payload_sha256,
        'audit_created', true
    );
end;
$function$;

revoke all on table public.nema_measurement_idempotency from anon, authenticated, service_role;
revoke all on table public.nema_measurement_audit from anon, authenticated, service_role;
revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;

-- The function owner has only the table rights the RPC needs. RLS remains enabled;
-- policies below are scoped only to this non-login role. No direct client policies exist.
grant usage on schema public to nema_measurement_writer;
grant usage on schema extensions to nema_measurement_writer;
grant select, insert on table public.nema_indicator_measurements to nema_measurement_writer;
grant select, insert on table public.nema_measurement_idempotency to nema_measurement_writer;
grant insert on table public.nema_measurement_audit to nema_measurement_writer;

drop policy if exists nema_measurement_writer_access on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_select on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_insert on public.nema_indicator_measurements;
create policy nema_measurement_writer_select on public.nema_indicator_measurements
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_indicator_measurements
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_select on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_idempotency;
create policy nema_measurement_writer_select on public.nema_measurement_idempotency
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_measurement_idempotency
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_audit;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_audit;
create policy nema_measurement_writer_insert on public.nema_measurement_audit
    for insert to nema_measurement_writer with check (true);

grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;
grant execute on function extensions.digest(bytea, text) to nema_measurement_writer;
grant select on table public.nema_measurement_idempotency to service_role;
grant select on table public.nema_measurement_audit to service_role;

revoke all on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    from public, anon, authenticated, service_role;

-- PostgreSQL requires the target owner to have CREATE on the containing schema
-- during ALTER FUNCTION OWNER. Grant it only for this ownership transfer, then
-- immediately revoke it so the SECURITY DEFINER owner cannot create schema objects.
grant create on schema public to nema_measurement_writer;
alter function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    owner to nema_measurement_writer;
revoke create on schema public from nema_measurement_writer;

grant execute on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    to service_role;

revoke all on function public.reject_nema_measurement_audit_mutation()
    from public, anon, authenticated, service_role;

commit;

-- REQUIRED before staging approval:
-- * Verify pgcrypto is installed in schema extensions before applying this migration.
-- * Validate database-computed digest parity and replay behavior on the target PostgreSQL version.
-- * Test concurrent duplicate requests, conflict, injected rollback, and unique-key collision.
-- * Verify function owner is nema_measurement_writer (NOLOGIN, NOINHERIT, no BYPASSRLS).
-- * Verify writer-role table grants and command-specific SELECT/INSERT RLS policies match this migration.
-- * Confirm RLS/grants and fixed search_path; verify no anon/authenticated execution.
-- * This RPC does not authenticate p_actor_id/p_actor_role; API must derive these from OIDC/session.
-- * Evidence bytes and reviewer independence require separate authenticated workflows.
        and split_part(object_key, '/', 2) = substr(split_part(object_key, '/', 3), 1, 2)
        and split_part(object_key, '/', 3) = pg_catalog.lower(sha256)
    ),
    constraint nema_evidence_id_nonblank check (length(pg_catalog.btrim(evidence_id)) > 0),
    constraint nema_evidence_actor_nonblank check (length(pg_catalog.btrim(registered_by)) > 0)
);

create table if not exists public.nema_measurement_audit (
    audit_id text primary key,
    measurement_id text not null
        references public.nema_indicator_measurements(measurement_id) on delete restrict,
    actor_id text not null,
    actor_role text not null,
    action text not null check (action = 'measurement_submitted'),
    idempotency_key text not null
        references public.nema_measurement_idempotency(idempotency_key) on delete restrict,
    payload_sha256 text not null check (payload_sha256 ~ '^[a-fA-F0-9]{64}$'),
    created_at timestamptz not null default pg_catalog.now(),
    constraint nema_measurement_audit_actor_nonblank check (length(pg_catalog.btrim(actor_id)) > 0)
);

create index if not exists idx_nema_measurement_audit_measurement_created
    on public.nema_measurement_audit (measurement_id, created_at, audit_id);

alter table public.nema_measurement_idempotency enable row level security;
alter table public.nema_measurement_audit enable row level security;

create or replace function public.reject_nema_measurement_audit_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
begin
    raise exception 'NEMA measurement audit events are append-only';
end;
$function$;

drop trigger if exists nema_measurement_audit_no_update on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_update
before update on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

drop trigger if exists nema_measurement_audit_no_delete on public.nema_measurement_audit;
create trigger nema_measurement_audit_no_delete
before delete on public.nema_measurement_audit
for each row execute function public.reject_nema_measurement_audit_mutation();

create or replace function public.submit_nema_indicator_measurement(
    p_measurement_id text,
    p_idempotency_key text,
    p_actor_id text,
    p_actor_role text,
    p_record jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_existing public.nema_measurement_idempotency%rowtype;
    v_value numeric;
    v_numerator numeric;
    v_denominator numeric;
    v_decision text;
    v_payload_sha256 text;
begin
    if p_measurement_id is null or length(pg_catalog.btrim(p_measurement_id)) = 0
       or length(pg_catalog.btrim(p_measurement_id)) > 256 then
        raise exception 'invalid measurement id' using errcode = '22023';
    end if;
    if p_idempotency_key is null or length(pg_catalog.btrim(p_idempotency_key)) = 0
       or length(pg_catalog.btrim(p_idempotency_key)) > 256 then
        raise exception 'invalid idempotency key' using errcode = '22023';
    end if;
    if p_actor_id is null or length(pg_catalog.btrim(p_actor_id)) = 0
       or length(pg_catalog.btrim(p_actor_id)) > 256 then
        raise exception 'invalid trusted actor id' using errcode = '22023';
    end if;
    -- NULL must be rejected explicitly: SQL three-valued logic makes `NULL NOT IN (...)` NULL, not TRUE.
    if p_actor_role is null or p_actor_role not in ('submitter', 'coordinator', 'admin') then
        raise exception 'actor role is not allowed to submit measurements' using errcode = '42501';
    end if;
    if p_record is null or pg_catalog.jsonb_typeof(p_record) <> 'object' then
        raise exception 'measurement record must be a JSON object' using errcode = '22023';
    end if;
    if p_record->>'status' is distinct from 'measured' then
        raise exception 'submission status must be measured; verification is a separate review action'
            using errcode = '22023';
    end if;
    if p_record->>'indicator_id' is null or length(pg_catalog.btrim(p_record->>'indicator_id')) = 0
       or p_record->>'definition_version' is null
       or length(pg_catalog.btrim(p_record->>'definition_version')) = 0
       or p_record->>'reporting_timezone' is null
       or length(pg_catalog.btrim(p_record->>'reporting_timezone')) = 0
       or p_record->>'unit' is null
       or length(pg_catalog.btrim(p_record->>'unit')) = 0
       or p_record->>'calculation_method' is null
       or length(pg_catalog.btrim(p_record->>'calculation_method')) = 0
       or p_record->>'reporting_period_start' is null
       or p_record->>'reporting_period_end' is null then
        raise exception 'required measurement fields are missing' using errcode = '22023';
    end if;
    -- IS DISTINCT FROM rejects SQL NULL as well as JSON values of the wrong type.
    -- Keep array length in a separate branch so it is never evaluated on a non-array.
    if pg_catalog.jsonb_typeof(p_record->'source_refs') is distinct from 'array' then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'source_refs') = 0 then
        raise exception 'measured records require source_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
         where pg_catalog.jsonb_typeof(source_ref.item) is distinct from 'string'
            or length(pg_catalog.btrim(source_ref.item #>> '{}')) = 0
    ) then
        raise exception 'source_refs entries must be non-empty strings' using errcode = '22023';
    end if;
    if (
        select count(*) <> count(distinct source_ref.item #>> '{}')
          from pg_catalog.jsonb_array_elements(p_record->'source_refs') as source_ref(item)
    ) then
        raise exception 'source_refs entries must be unique' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_typeof(p_record->'evidence_refs') is distinct from 'array' then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if pg_catalog.jsonb_array_length(p_record->'evidence_refs') = 0 then
        raise exception 'measured records require evidence_refs array' using errcode = '22023';
    end if;
    if exists (
        select 1
          from pg_catalog.jsonb_array_elements(p_record->'evidence_refs') as evidence_ref(item)
         where pg_catalog.jsonb_typeof(evidence_ref.item) is distinct from 'object'
            or pg_catalog.jsonb_typeof(evidence_ref.item->'reference') is distinct from 'string'
            or length(pg_catalog.btrim(evidence_ref.item->>'reference')) = 0
            or pg_catalog.jsonb_typeof(evidence_ref.item->'sha256') is distinct from 'string'
            or (evidence_ref.item->>'sha256') !~ '^[A-Fa-f0-9]{64}$'
    ) then
        raise exception 'evidence_refs require a reference and a valid SHA-256 digest' using errcode = '22023';
    end if;
    if p_record ? 'exclusions' and pg_catalog.jsonb_typeof(p_record->'exclusions') is distinct from 'array' then
        raise exception 'exclusions must be an array' using errcode = '22023';
    end if;
    if p_record ? 'caveats' and pg_catalog.jsonb_typeof(p_record->'caveats') is distinct from 'array' then
        raise exception 'caveats must be an array' using errcode = '22023';
    end if;

    begin
        v_value := (p_record->>'value')::numeric;
        if p_record ? 'numerator' then v_numerator := (p_record->>'numerator')::numeric; end if;
        if p_record ? 'denominator' then v_denominator := (p_record->>'denominator')::numeric; end if;
    exception when others then
        raise exception 'value, numerator, or denominator is not numeric' using errcode = '22023';
    end;
    if v_value is null or v_value < 0 or v_value = 'NaN'::numeric
       or v_value = 'Infinity'::numeric or v_value = '-Infinity'::numeric then
        raise exception 'value must be a finite non-negative number' using errcode = '22023';
    end if;
    if v_numerator is not null and (v_numerator < 0 or v_numerator = 'NaN'::numeric
       or v_numerator = 'Infinity'::numeric or v_numerator = '-Infinity'::numeric) then
        raise exception 'numerator must be finite and non-negative' using errcode = '22023';
    end if;
    if v_denominator is not null and (v_denominator <= 0 or v_denominator = 'NaN'::numeric
       or v_denominator = 'Infinity'::numeric or v_denominator = '-Infinity'::numeric) then
        raise exception 'denominator must be finite and positive' using errcode = '22023';
    end if;
    if v_numerator is not null and v_denominator is not null and v_numerator > v_denominator then
        raise exception 'numerator cannot exceed denominator' using errcode = '22023';
    end if;
    begin
        if (p_record->>'reporting_period_start')::date > (p_record->>'reporting_period_end')::date then
            raise exception 'reporting period end precedes start' using errcode = '22023';
        end if;
    exception when sqlstate '22023' then
        raise;
    when others then
        raise exception 'reporting period dates must be valid ISO dates' using errcode = '22023';
    end;

    -- Compute the digest inside PostgreSQL from the actual database payload. jsonb::text has
    -- deterministic key ordering and formatting within PostgreSQL; the API must not supply a digest.
    v_payload_sha256 := pg_catalog.encode(
        extensions.digest(
            pg_catalog.convert_to(
                pg_catalog.jsonb_build_object('measurement_id', p_measurement_id, 'record', p_record)::text,
                'UTF8'
            ),
            'sha256'
        ),
        'hex'
    );

    -- Serialize requests using the same key so concurrent retries cannot both create a record.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_idempotency_key, 0)
    );
    select * into v_existing
      from public.nema_measurement_idempotency
     where idempotency_key = p_idempotency_key;
    if found then
        if pg_catalog.lower(v_existing.payload_sha256) <> v_payload_sha256 then
            raise exception 'idempotency key reused with a different payload' using errcode = '23505';
        end if;
        return pg_catalog.jsonb_build_object(
            'decision', 'replay',
            'measurement_id', v_existing.measurement_id,
            'payload_sha256', v_existing.payload_sha256,
            'audit_created', false
        );
    end if;

    insert into public.nema_indicator_measurements (
        measurement_id, indicator_id, definition_version, reporting_period_start,
        reporting_period_end, reporting_timezone, status, value, unit, numerator,
        denominator, exclusions, source_refs, evidence_refs, calculation_method,
        reviewer_id, verified_at, caveats
    ) values (
        p_measurement_id, p_record->>'indicator_id', p_record->>'definition_version',
        (p_record->>'reporting_period_start')::date, (p_record->>'reporting_period_end')::date,
        p_record->>'reporting_timezone', 'measured', v_value, p_record->>'unit',
        v_numerator, v_denominator,
        coalesce(p_record->'exclusions', '[]'::jsonb),
        p_record->'source_refs', coalesce(p_record->'evidence_refs', '[]'::jsonb),
        p_record->>'calculation_method', null, null, coalesce(p_record->'caveats', '[]'::jsonb)
    );

    insert into public.nema_measurement_idempotency (
        idempotency_key, payload_sha256, measurement_id
    ) values (p_idempotency_key, v_payload_sha256, p_measurement_id);

    insert into public.nema_measurement_audit (
        audit_id, measurement_id, actor_id, actor_role, action, idempotency_key, payload_sha256
    ) values (
        p_measurement_id || ':submitted', p_measurement_id, p_actor_id, p_actor_role,
        'measurement_submitted', p_idempotency_key, v_payload_sha256
    );

    return pg_catalog.jsonb_build_object(
        'decision', 'new',
        'measurement_id', p_measurement_id,
        'payload_sha256', v_payload_sha256,
        'audit_created', true
    );
end;
$function$;

revoke all on table public.nema_measurement_idempotency from anon, authenticated, service_role;
revoke all on table public.nema_measurement_audit from anon, authenticated, service_role;
revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;

-- The function owner has only the table rights the RPC needs. RLS remains enabled;
-- policies below are scoped only to this non-login role. No direct client policies exist.
grant usage on schema public to nema_measurement_writer;
grant usage on schema extensions to nema_measurement_writer;
grant select, insert on table public.nema_indicator_measurements to nema_measurement_writer;
grant select, insert on table public.nema_measurement_idempotency to nema_measurement_writer;
grant insert on table public.nema_measurement_audit to nema_measurement_writer;

drop policy if exists nema_measurement_writer_access on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_select on public.nema_indicator_measurements;
drop policy if exists nema_measurement_writer_insert on public.nema_indicator_measurements;
create policy nema_measurement_writer_select on public.nema_indicator_measurements
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_indicator_measurements
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_select on public.nema_measurement_idempotency;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_idempotency;
create policy nema_measurement_writer_select on public.nema_measurement_idempotency
    for select to nema_measurement_writer using (true);
create policy nema_measurement_writer_insert on public.nema_measurement_idempotency
    for insert to nema_measurement_writer with check (true);

drop policy if exists nema_measurement_writer_access on public.nema_measurement_audit;
drop policy if exists nema_measurement_writer_insert on public.nema_measurement_audit;
create policy nema_measurement_writer_insert on public.nema_measurement_audit
    for insert to nema_measurement_writer with check (true);

grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;
grant execute on function extensions.digest(bytea, text) to nema_measurement_writer;
grant select on table public.nema_measurement_idempotency to service_role;
grant select on table public.nema_measurement_audit to service_role;

revoke all on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    from public, anon, authenticated, service_role;

-- PostgreSQL requires the target owner to have CREATE on the containing schema
-- during ALTER FUNCTION OWNER. Grant it only for this ownership transfer, then
-- immediately revoke it so the SECURITY DEFINER owner cannot create schema objects.
grant create on schema public to nema_measurement_writer;
alter function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    owner to nema_measurement_writer;
revoke create on schema public from nema_measurement_writer;

grant execute on function public.submit_nema_indicator_measurement(text, text, text, text, jsonb)
    to service_role;

revoke all on function public.reject_nema_measurement_audit_mutation()
    from public, anon, authenticated, service_role;

commit;

-- REQUIRED before staging approval:
-- * Verify pgcrypto is installed in schema extensions before applying this migration.
-- * Validate database-computed digest parity and replay behavior on the target PostgreSQL version.
-- * Test concurrent duplicate requests, conflict, injected rollback, and unique-key collision.
-- * Verify function owner is nema_measurement_writer (NOLOGIN, NOINHERIT, no BYPASSRLS).
-- * Verify writer-role table grants and command-specific SELECT/INSERT RLS policies match this migration.
-- * Confirm RLS/grants and fixed search_path; verify no anon/authenticated execution.
-- * This RPC does not authenticate p_actor_id/p_actor_role; API must derive these from OIDC/session.
-- * Evidence bytes and reviewer independence require separate authenticated workflows.