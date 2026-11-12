-- Local seed data for Phase 1 testing and development
-- Creates two deterministic test users in auth.users for local RLS verification

DO $$
DECLARE
    user_a_id UUID := 'a0000000-0000-0000-0000-000000000001'::uuid;
    user_b_id UUID := 'b0000000-0000-0000-0000-000000000002'::uuid;
BEGIN
    -- Insert test user A if not exists
    IF NOT EXISTS (SELECT 1 FROM auth.users WHERE id = user_a_id) THEN
        INSERT INTO auth.users (
            instance_id,
            id,
            aud,
            role,
            email,
            encrypted_password,
            email_confirmed_at,
            raw_app_meta_data,
            raw_user_meta_data,
            created_at,
            updated_at
        ) VALUES (
            '00000000-0000-0000-0000-000000000000',
            user_a_id,
            'authenticated',
            'authenticated',
            'user_a@test.local',
            extensions.crypt('password123', extensions.gen_salt('bf')),
            NOW(),
            '{"provider": "email", "providers": ["email"]}'::jsonb,
            '{"name": "Test User A"}'::jsonb,
            NOW(),
            NOW()
        );
    END IF;

    -- Insert test user B if not exists
    IF NOT EXISTS (SELECT 1 FROM auth.users WHERE id = user_b_id) THEN
        INSERT INTO auth.users (
            instance_id,
            id,
            aud,
            role,
            email,
            encrypted_password,
            email_confirmed_at,
            raw_app_meta_data,
            raw_user_meta_data,
            created_at,
            updated_at
        ) VALUES (
            '00000000-0000-0000-0000-000000000000',
            user_b_id,
            'authenticated',
            'authenticated',
            'user_b@test.local',
            extensions.crypt('password123', extensions.gen_salt('bf')),
            NOW(),
            '{"provider": "email", "providers": ["email"]}'::jsonb,
            '{"name": "Test User B"}'::jsonb,
            NOW(),
            NOW()
        );
    END IF;
END $$;
