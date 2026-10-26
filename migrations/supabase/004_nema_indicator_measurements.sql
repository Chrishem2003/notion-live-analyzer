-- NEMA-AGORA evidence-backed indicator measurement ledger.
-- NOT applied automatically. Review and apply only to the intended staging project
-- after checking migration 001 and confirming the project URL.
-- This creates a schema contract only: client roles have no access and service_role
-- receives SELECT only. Writes must be added later through an audited transactional RPC.

begin;

create table if not exists public.nema_indicator_measurements (
    measurement_id text primary key,
    indicator_id text not null,
    definition_version text not null,
    reporting_period_start date not null,
    reporting_period_end date not null,
    reporting_timezone text not null,
    status text not null check (
        status in ('not_started', 'in_progress', 'measured', 'verified', 'blocked')
    ),
    value numeric,
    unit text not null,
    numerator numeric,
    denominator numeric,
    exclusions jsonb not null default '[]'::jsonb,
    source_refs jsonb not null default '[]'::jsonb,
    evidence_refs jsonb not null default '[]'::jsonb,
    calculation_method text,
    reviewer_id text,
    verified_at timestamptz,
    caveats jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now(),
    constraint nema_indicator_period_valid
        check (reporting_period_end >= reporting_period_start),
    constraint nema_indicator_value_nonnegative
        check (value is null or value >= 0),
    constraint nema_indicator_numerator_nonnegative
        check (numerator is null or numerator >= 0),
    constraint nema_indicator_denominator_nonnegative
        check (denominator is null or denominator >= 0),
    constraint nema_indicator_numerator_le_denominator
        check (numerator is null or denominator is null or numerator <= denominator),
    constraint nema_indicator_json_arrays check (
        jsonb_typeof(exclusions) = 'array'
        and jsonb_typeof(source_refs) = 'array'
        and jsonb_typeof(evidence_refs) = 'array'
        and jsonb_typeof(caveats) = 'array'
    ),
    constraint nema_indicator_verified_has_evidence check (
        status <> 'verified'
        or (
            value is not null
            and jsonb_array_length(source_refs) > 0
            and jsonb_array_length(evidence_refs) > 0
            and calculation_method is not null
            and length(trim(calculation_method)) > 0
            and reviewer_id is not null
            and length(trim(reviewer_id)) > 0
            and verified_at is not null
        )
    ),
    constraint nema_indicator_measured_has_source check (
        status not in ('measured', 'verified')
        or (
            value is not null
            and jsonb_array_length(source_refs) > 0
            and calculation_method is not null
            and length(trim(calculation_method)) > 0
        )
    )
);

create index if not exists idx_nema_indicator_period
    on public.nema_indicator_measurements
       (indicator_id, reporting_period_start desc, reporting_period_end desc, measurement_id);

alter table public.nema_indicator_measurements enable row level security;

revoke all on table public.nema_indicator_measurements from anon, authenticated, service_role;
grant usage on schema public to service_role;
grant select on table public.nema_indicator_measurements to service_role;

comment on table public.nema_indicator_measurements is
    'Evidence-backed NEMA-AGORA measurements. Targets are defined in versioned application registry and are not stored as achieved results.';
comment on column public.nema_indicator_measurements.source_refs is
    'JSON array of stable source record or dataset references; do not store secrets or unnecessary personal data.';
comment on column public.nema_indicator_measurements.evidence_refs is
    'JSON array of reviewable artifact references; verified status requires at least one reference.';

commit;

-- Verification after an approved apply:
-- 1) confirm RLS is enabled;
-- 2) confirm anon/authenticated have no privileges;
-- 3) confirm service_role has SELECT only;
-- 4) insert no test or production records until a separate audited write RPC is approved.
