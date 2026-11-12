-- Migration: 20261112000001_core_schema_and_rls.sql
-- Description: Phase 1 (M1.1) Core schema tables, indexes, Row-Level Security (RLS) policies, and audit function.

-- 1. Ensure required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";

-- 2. Create Core Tables in public schema

-- 2a. user_settings
CREATE TABLE IF NOT EXISTS public.user_settings (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE DEFAULT auth.uid(),
    memory_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2b. conversations
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE DEFAULT auth.uid(),
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2c. messages
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE DEFAULT auth.uid(),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2d. runs
CREATE TABLE IF NOT EXISTS public.runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    message_id UUID REFERENCES public.messages(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE DEFAULT auth.uid(),
    pipeline TEXT NOT NULL DEFAULT 'system_a',
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'awaiting_user', 'awaiting_approval', 'completed', 'abstained', 'failed', 'cancelled')) DEFAULT 'queued',
    total_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0,
    latency_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 2e. audit_log
CREATE TABLE IF NOT EXISTS public.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. B-Tree Indexes on (user_id, created_at)
CREATE INDEX IF NOT EXISTS idx_conversations_user_created ON public.conversations (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_user_created ON public.messages (user_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON public.messages (conversation_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_runs_user_created ON public.runs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_conversation_created ON public.runs (conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_created ON public.audit_log (user_id, created_at DESC);

-- 4. Enable Row-Level Security (RLS) on ALL tables
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- 5. RLS Policies

-- 5a. user_settings policies
CREATE POLICY "user_settings_select_own"
    ON public.user_settings FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "user_settings_insert_own"
    ON public.user_settings FOR INSERT
    TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "user_settings_update_own"
    ON public.user_settings FOR UPDATE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "user_settings_delete_own"
    ON public.user_settings FOR DELETE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- 5b. conversations policies
CREATE POLICY "conversations_select_own"
    ON public.conversations FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "conversations_insert_own"
    ON public.conversations FOR INSERT
    TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "conversations_update_own"
    ON public.conversations FOR UPDATE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "conversations_delete_own"
    ON public.conversations FOR DELETE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- 5c. messages policies (ensuring message cannot reference another user's conversation)
CREATE POLICY "messages_select_own"
    ON public.messages FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "messages_insert_own"
    ON public.messages FOR INSERT
    TO authenticated
    WITH CHECK (
        (SELECT auth.uid()) = user_id
        AND EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = conversation_id AND c.user_id = (SELECT auth.uid())
        )
    );

CREATE POLICY "messages_update_own"
    ON public.messages FOR UPDATE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK (
        (SELECT auth.uid()) = user_id
        AND EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = conversation_id AND c.user_id = (SELECT auth.uid())
        )
    );

CREATE POLICY "messages_delete_own"
    ON public.messages FOR DELETE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- 5d. runs policies (ensuring run cannot reference another user's conversation)
CREATE POLICY "runs_select_own"
    ON public.runs FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "runs_insert_own"
    ON public.runs FOR INSERT
    TO authenticated
    WITH CHECK (
        (SELECT auth.uid()) = user_id
        AND EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = conversation_id AND c.user_id = (SELECT auth.uid())
        )
    );

CREATE POLICY "runs_update_own"
    ON public.runs FOR UPDATE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK (
        (SELECT auth.uid()) = user_id
        AND EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = conversation_id AND c.user_id = (SELECT auth.uid())
        )
    );

CREATE POLICY "runs_delete_own"
    ON public.runs FOR DELETE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- 5e. audit_log policies
-- SELECT-only for authenticated users on their own records.
-- Direct INSERT, UPDATE, DELETE for users are forbidden.
CREATE POLICY "audit_log_select_own"
    ON public.audit_log FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- 6. Trusted Security Definer Function for writing audit logs
CREATE OR REPLACE FUNCTION public.write_audit_log(
    p_user_id UUID,
    p_event_type TEXT,
    p_resource_type TEXT DEFAULT NULL,
    p_resource_id TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_audit_id UUID;
BEGIN
    INSERT INTO public.audit_log (
        user_id,
        event_type,
        resource_type,
        resource_id,
        metadata,
        created_at
    ) VALUES (
        p_user_id,
        p_event_type,
        p_resource_type,
        p_resource_id,
        COALESCE(p_metadata, '{}'::jsonb),
        NOW()
    )
    RETURNING id INTO v_audit_id;

    RETURN v_audit_id;
END;
$$;

-- Grant execution to authenticated role
GRANT EXECUTE ON FUNCTION public.write_audit_log TO authenticated;
