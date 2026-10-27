-- NEMA-AGORA ownership integrity guard (read-only phase).
-- Apply only after 002_nema_case_owner_scope.sql on the intended staging project.
-- This prevents reassignment after an owner has been assigned. It does not grant
-- writes, backfill legacy ownership, or enable submitter API access.
--
-- Initial owner assignment must later be performed only by an audited,
-- privileged transaction/RPC after identity and evidence have been verified.

begin;

create or replace function public.prevent_nema_case_owner_reassignment()
returns trigger
language plpgsql
as $$
begin
    if old.owner_id is not null and new.owner_id is distinct from old.owner_id then
        raise exception 'NEMA case ownership cannot be reassigned';
    end if;
    return new;
end;
$$;

drop trigger if exists nema_cases_owner_immutable on public.nema_cases;
create trigger nema_cases_owner_immutable
before update of owner_id on public.nema_cases
for each row execute function public.prevent_nema_case_owner_reassignment();

comment on function public.prevent_nema_case_owner_reassignment() is
    'Prevents changing an already assigned NEMA case owner. Initial assignment requires a separately authorized and audited operation.';

commit;

-- Verification: inspect trigger definition and confirm service_role still has
-- SELECT only on nema_cases/nema_case_audit. Do not enable direct table writes.
