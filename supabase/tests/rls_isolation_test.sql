-- ==============================================================================
-- RLS Two-User Isolation Automated Test Suite (Phase 1, M1.1)
-- Formatted for pgTAP (supabase test db)
-- ==============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgtap;

-- Plan: Exactly 18 assertions
SELECT plan(18);

-- ==============================================================================
-- 1. Verify RLS is enabled on all 5 public tables (Tests 1-5)
-- ==============================================================================
SELECT ok(
    (SELECT relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'user_settings'),
    'user_settings table has RLS enabled'
);

SELECT ok(
    (SELECT relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'conversations'),
    'conversations table has RLS enabled'
);

SELECT ok(
    (SELECT relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'messages'),
    'messages table has RLS enabled'
);

SELECT ok(
    (SELECT relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'runs'),
    'runs table has RLS enabled'
);

SELECT ok(
    (SELECT relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relname = 'audit_log'),
    'audit_log table has RLS enabled'
);

-- ==============================================================================
-- 2. User A: Insert and Read Own Resources (Tests 6-9)
-- ==============================================================================
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" TO '{"sub": "a0000000-0000-0000-0000-000000000001", "role": "authenticated"}';

-- Clean any existing records for User A
DELETE FROM public.conversations WHERE user_id = 'a0000000-0000-0000-0000-000000000001'::uuid;
DELETE FROM public.user_settings WHERE user_id = 'a0000000-0000-0000-0000-000000000001'::uuid;

-- Insert User A resources
INSERT INTO public.user_settings (user_id, memory_enabled)
VALUES ('a0000000-0000-0000-0000-000000000001'::uuid, true);

INSERT INTO public.conversations (id, user_id, title)
VALUES ('a0000000-0000-0000-0000-000000000010'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'User A Investigation');

INSERT INTO public.messages (id, conversation_id, user_id, role, content)
VALUES ('a0000000-0000-0000-0000-000000000020'::uuid, 'a0000000-0000-0000-0000-000000000010'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'user', 'Status check');

INSERT INTO public.runs (id, conversation_id, message_id, user_id, pipeline, status)
VALUES ('a0000000-0000-0000-0000-000000000030'::uuid, 'a0000000-0000-0000-0000-000000000010'::uuid, 'a0000000-0000-0000-0000-000000000020'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'system_a', 'running');

SELECT is(
    (SELECT COUNT(*)::integer FROM public.conversations WHERE id = 'a0000000-0000-0000-0000-000000000010'::uuid),
    1,
    'User A can read own conversation'
);

SELECT is(
    (SELECT COUNT(*)::integer FROM public.messages WHERE id = 'a0000000-0000-0000-0000-000000000020'::uuid),
    1,
    'User A can read own message'
);

SELECT is(
    (SELECT COUNT(*)::integer FROM public.runs WHERE id = 'a0000000-0000-0000-0000-000000000030'::uuid),
    1,
    'User A can read own run'
);

-- Write audit log via SECURITY DEFINER function
SELECT is(
    (SELECT COUNT(*)::integer FROM (
        SELECT public.write_audit_log('a0000000-0000-0000-0000-000000000001'::uuid, 'test_event', 'conversation', 'a0000000-0000-0000-0000-000000000010')
    ) t),
    1,
    'User A can write audit log via security definer function'
);

-- ==============================================================================
-- 3. User B: Cross-User Isolation (Tests 10-18)
-- ==============================================================================
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" TO '{"sub": "b0000000-0000-0000-0000-000000000002", "role": "authenticated"}';

-- 3a. SELECT across User A records must return 0 rows (Tests 10-14)
SELECT is(
    (SELECT COUNT(*)::integer FROM public.user_settings WHERE user_id = 'a0000000-0000-0000-0000-000000000001'::uuid),
    0,
    'User B gets 0 rows on SELECT from User A user_settings'
);

SELECT is(
    (SELECT COUNT(*)::integer FROM public.conversations WHERE user_id = 'a0000000-0000-0000-0000-000000000001'::uuid),
    0,
    'User B gets 0 rows on SELECT from User A conversations'
);

SELECT is(
    (SELECT COUNT(*)::integer FROM public.messages WHERE user_id = 'a0000000-0000-0000-0000-000000000001'::uuid),
    0,
    'User B gets 0 rows on SELECT from User A messages'
);

SELECT is(
    (SELECT COUNT(*)::integer FROM public.runs WHERE user_id = 'a0000000-0000-0000-0000-000000000001'::uuid),
    0,
    'User B gets 0 rows on SELECT from User A runs'
);

SELECT is(
    (SELECT COUNT(*)::integer FROM public.audit_log WHERE user_id = 'a0000000-0000-0000-0000-000000000001'::uuid),
    0,
    'User B gets 0 rows on SELECT from User A audit_log'
);

-- 3b. UPDATE & DELETE against User A records (0 rows affected) (Tests 15-16)
DO $$
DECLARE
    affected integer;
BEGIN
    UPDATE public.conversations SET title = 'Hacked' WHERE id = 'a0000000-0000-0000-0000-000000000010'::uuid;
    GET DIAGNOSTICS affected = ROW_COUNT;
    IF affected <> 0 THEN RAISE EXCEPTION 'UPDATE affected % rows', affected; END IF;
END $$;
SELECT pass('User B cannot UPDATE User A conversation (0 rows affected)');

DO $$
DECLARE
    affected integer;
BEGIN
    DELETE FROM public.conversations WHERE id = 'a0000000-0000-0000-0000-000000000010'::uuid;
    GET DIAGNOSTICS affected = ROW_COUNT;
    IF affected <> 0 THEN RAISE EXCEPTION 'DELETE affected % rows', affected; END IF;
END $$;
SELECT pass('User B cannot DELETE User A conversation (0 rows affected)');

-- 3c. Cross-user INSERT into User A's conversation must throw policy violation (Test 17)
SELECT throws_ok(
    $$ INSERT INTO public.messages (conversation_id, user_id, role, content)
       VALUES ('a0000000-0000-0000-0000-000000000010'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'user', 'Injected') $$,
    '42501',
    NULL,
    'User B cannot insert message into User A conversation'
);

-- 3d. Direct INSERT into audit_log must throw policy violation (Test 18)
SELECT throws_ok(
    $$ INSERT INTO public.audit_log (user_id, event_type)
       VALUES ('b0000000-0000-0000-0000-000000000002'::uuid, 'forged_event') $$,
    '42501',
    NULL,
    'Authenticated user cannot directly INSERT into audit_log'
);

-- ==============================================================================
-- Finish Test Suite
-- ==============================================================================
SELECT * FROM finish();

ROLLBACK;
