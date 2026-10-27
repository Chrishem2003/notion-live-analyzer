-- NEMA-AGORA ownership metadata for scoped, read-only case access.
-- Existing rows intentionally remain unowned (NULL) and must stay inaccessible to submitters
-- until a separately approved, evidence-backed ownership backfill is performed.
-- This migration does not grant writes or enable submitter API access.

begin;

alter table public.nema_cases
    add column if not exists owner_id text;

create index if not exists idx_nema_cases_owner_created
    on public.nema_cases (owner_id, created_at desc, case_id asc);

comment on column public.nema_cases.owner_id is
    'Stable authenticated issuer|subject key. NULL means unowned/legacy and must not be exposed to submitters.';

commit;

-- Verify column and index exist before deploying code that filters by owner_id.
-- Never assign historical rows to an owner by guessing from display name or reporter text.