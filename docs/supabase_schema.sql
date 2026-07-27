-- Schema for the Supabase account backend (modules/accounts.py).
-- Run once in Supabase → SQL Editor, then set SUPABASE_URL and
-- SUPABASE_SERVICE_KEY. The app reaches PostgREST with the service key, so RLS
-- policies below deny everything to anon/authenticated clients on purpose:
-- browsers never talk to these tables directly.

create table if not exists public.accounts (
    id text primary key,
    email text not null unique,
    password_hash text not null,
    tier text not null default 'free',
    created_at timestamptz not null default now(),
    trial_ends_at timestamptz,
    subscription_ends_at timestamptz,
    country text,
    institution text,
    student_verified boolean not null default false,
    notion_template_claimed boolean not null default false,
    stripe_customer_id text,
    is_admin boolean not null default false,
    is_suspended boolean not null default false
);

create table if not exists public.usage_events (
    id bigserial primary key,
    user_id text not null references public.accounts(id) on delete cascade,
    feature text not null,
    period text not null,
    used_at timestamptz not null default now()
);
create index if not exists idx_usage_user_period
    on public.usage_events (user_id, feature, period);

create table if not exists public.template_claims (
    token text primary key,
    user_id text not null references public.accounts(id) on delete cascade,
    issued_at timestamptz not null default now(),
    expires_at timestamptz not null,
    redeemed_at timestamptz
);

create table if not exists public.discount_codes (
    code text primary key,
    percent_off integer not null default 0,
    grants_tier text,
    grants_days integer,
    max_redemptions integer not null default 1,
    redemptions integer not null default 0,
    expires_at timestamptz,
    created_at timestamptz not null default now()
);

-- Lock the tables down: only the service key (which bypasses RLS) may read them.
alter table public.accounts enable row level security;
alter table public.usage_events enable row level security;
alter table public.template_claims enable row level security;
alter table public.discount_codes enable row level security;
