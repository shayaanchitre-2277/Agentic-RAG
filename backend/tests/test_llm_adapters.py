"""
Unit tests for LLM abstraction layer, FakeClient, provider factory,
secret redaction, and graceful Langfuse fallbacks.
"""

import pytest

from backend.app.core.config import settings
from backend.app.llm.base import LLMMessage, LLMRequest
from backend.app.llm.fake_client import FakeClient
from backend.app.llm.gemini_client import GeminiClient
from backend.app.llm.registry import get_llm_client, resolve_model_for_role
from backend.app.observability.redaction import redact_secrets
from backend.app.observability.tracing import trace_generation


@pytest.mark.anyio
async def test_fake_client_generate():
    client = FakeClient(fixed_response="Simulated answer.")
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="Hello test")],
        role_name="assistant",
    )
    result = await client.generate(request)

    assert result.content == "Simulated answer."
    assert result.provider == "fake"
    assert result.total_tokens > 0
    assert result.estimated_cost_usd == 0.0
    assert result.trace_id is not None


def test_registry_provider_factory():
    # Test fake provider
    settings.LLM_PROVIDER = "fake"
    client = get_llm_client()
    assert isinstance(client, FakeClient)

    # Test role resolution
    assert resolve_model_for_role("planner") == "gemini-3.8-flash"
    assert resolve_model_for_role("unknown_role") == settings.GEMINI_DEFAULT_MODEL


def test_secret_redaction_utility():
    raw_text = (
        "Here is my API key: AIzaSyD12345678901234567890123456789012 "
        "and token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_token_string "
        "and openai sk-123456789012345678901234567890"
    )
    scrubbed = redact_secrets(raw_text)

    assert "AIzaSy" not in scrubbed
    assert "[REDACTED_GEMINI_KEY]" in scrubbed
    assert "[REDACTED_TOKEN]" in scrubbed
    assert "[REDACTED_OPENAI_KEY]" in scrubbed


def test_graceful_langfuse_fallback():
    # Ensure trace_generation does not throw an error when Langfuse keys are absent
    settings.LANGFUSE_PUBLIC_KEY = None
    settings.LANGFUSE_SECRET_KEY = None

    trace_id = trace_generation(
        name="test_trace",
        model="fake-model",
        input_data={"prompt": "test prompt"},
        output_data={"text": "test output"},
    )
    assert trace_id.startswith("local-trace-")
