"""
Application configuration using pydantic-settings.
Reads environment variables for Supabase, LLM providers, and Langfuse tracing.

Strict Security:
  - SUPABASE_SERVICE_ROLE_KEY is strictly excluded from request-path settings.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App environment
    APP_ENV: str = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Supabase public client settings (Local defaults)
    SUPABASE_URL: str = "http://127.0.0.1:54321"
    SUPABASE_ANON_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.placeholder"

    # JWT Verification configuration
    SUPABASE_JWT_SECRET: Optional[str] = "super-secret-jwt-token-with-at-least-32-characters-long"
    SUPABASE_JWT_ALGORITHM: str = "HS256"
    SUPABASE_JWKS_URL: Optional[str] = None

    # LLM Provider Configuration (M1.3)
    # Supports "gemini" (default) or "fake" (for testing/cost-free operation)
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = ""
    GEMINI_DEFAULT_MODEL: str = "gemini-3.8-flash"

    # Langfuse Observability & Tracing (M1.3)
    LANGFUSE_ENABLED: bool = True
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
