"""
User-scoped database client dependency.
Initializes Supabase client with SUPABASE_URL + SUPABASE_ANON_KEY and attaches
the caller's verified Bearer JWT so PostgreSQL Row-Level Security (RLS) is strictly enforced.

Strict Architectural Rule (ADR-002):
  - NO service-role key is ever imported, configured, or used in request paths.
"""

from fastapi import Depends

from backend.app.core.config import settings
from backend.app.core.security import AuthenticatedUser, get_current_user
from supabase import Client, ClientOptions, create_client


def get_user_db(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Client:
    """
    Creates a user-scoped Supabase client authenticated under the caller's JWT.
    All SQL operations through this client execute with the caller's auth.uid(),
    ensuring RLS policies isolate tenant records.
    """
    headers = {
        "Authorization": f"Bearer {current_user.raw_token}",
    }
    options = ClientOptions(headers=headers)
    client: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
        options=options,
    )
    # Ensure postgrest client explicitly includes auth header
    client.postgrest.auth(current_user.raw_token)
    return client
