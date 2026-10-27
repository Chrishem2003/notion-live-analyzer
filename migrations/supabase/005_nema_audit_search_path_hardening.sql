-- NEMA-AGORA security hardening: pin the append-only audit trigger function's search_path.
-- This is an additive function-configuration change only. It does not modify rows,
-- grant permissions, change RLS, or enable case/audit writes.
-- Apply only to the explicitly approved staging project after reviewing the target project URL.

begin;

alter function public.reject_nema_case_audit_mutation()
    set search_path = pg_catalog;

commit;

-- Verification after approved application:
--   select p.proname, p.proconfig
--   from pg_proc p
--   join pg_namespace n on n.oid = p.pronamespace
--   where n.nspname = 'public'
--     and p.proname = 'reject_nema_case_audit_mutation';
-- Expected: proconfig contains search_path=pg_catalog.
-- Also confirm the existing append-only triggers remain attached and RLS is still enabled.
-- This migration must not be applied to production as part of this integration phase.
