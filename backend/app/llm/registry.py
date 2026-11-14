"""
Role-to-model registry and provider factory.
Allows switching providers via configuration (LLM_PROVIDER="fake" vs "gemini").
"""

from typing import Dict
from backend.app.core.config import settings
from backend.app.llm.base import LLMClient
from backend.app.llm.fake_client import FakeClient
from backend.app.llm.gemini_client import GeminiClient

# Role-to-model mapping default
ROLE_MODELS: Dict[str, str] = {
    "default": "gemini-3.8-flash",
    "assistant": "gemini-3.8-flash",
    "planner": "gemini-3.8-flash",
    "researcher": "gemini-3.8-flash",
    "verifier": "gemini-3.8-flash",
    "synthesiser": "gemini-3.8-flash",
    "judge": "gemini-3.8-flash",
}


def resolve_model_for_role(role_name: str) -> str:
    """Returns the configured model string for a given role."""
    return ROLE_MODELS.get(role_name.lower(), settings.GEMINI_DEFAULT_MODEL)


def get_llm_client() -> LLMClient:
    """
    Factory function providing the active LLMClient based on settings.LLM_PROVIDER.
    Pure configuration-based switching without modifying application logic.
    """
    provider = settings.LLM_PROVIDER.lower().strip()
    if provider == "fake":
        return FakeClient()
    elif provider == "gemini":
        return GeminiClient()
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'. Supported: 'gemini', 'fake'")
