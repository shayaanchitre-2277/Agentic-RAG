"""
Secret redaction utility.
Scrubs API keys, Bearer tokens, private passwords, and known credential patterns
from strings before logging or emitting to telemetry (e.g., Langfuse traces).
"""

import re
from typing import Any

# Compiled regex patterns for credential detection
REDACTION_PATTERNS = [
    # Bearer tokens
    (re.compile(r"Bearer\s+([A-Za-z0-9\-_\.\~]{15,})", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    # Generic API key patterns
    (re.compile(r"(api[_-]?key\s*[:=]\s*)['\"]?([A-Za-z0-9\-_\.]{12,})['\"]?", re.IGNORECASE), r"\1[REDACTED_API_KEY]"),
    # Google AI Studio API Keys (AIzaSy...)
    (re.compile(r"AIzaSy[A-Za-z0-9\-_]{33}", re.IGNORECASE), "[REDACTED_GEMINI_KEY]"),
    # OpenAI API Keys (sk-...)
    (re.compile(r"sk-[A-Za-z0-9\-_]{20,}", re.IGNORECASE), "[REDACTED_OPENAI_KEY]"),
    # Atlassian tokens (ATATT...)
    (re.compile(r"ATATT[A-Za-z0-9\-_]{50,}", re.IGNORECASE), "[REDACTED_ATLASSIAN_TOKEN]"),
    # Basic Authorization headers
    (re.compile(r"Basic\s+([A-Za-z0-9+/=]{15,})", re.IGNORECASE), "Basic [REDACTED_BASIC_AUTH]"),
]


def redact_secrets(content: Any) -> Any:
    """
    Recursively scrubs secrets from strings, dictionaries, lists, or general objects.
    """
    if isinstance(content, str):
        redacted = content
        for pattern, replacement in REDACTION_PATTERNS:
            redacted = pattern.sub(replacement, redacted)
        return redacted
    elif isinstance(content, dict):
        return {k: redact_secrets(v) for k, v in content.items()}
    elif isinstance(content, list):
        return [redact_secrets(item) for item in content]
    return content
