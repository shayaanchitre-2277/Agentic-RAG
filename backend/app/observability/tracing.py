"""
Langfuse Tracing wrapper.
Creates a trace and generation per LLM call, recording model, role, tokens, latency,
and redacted prompt/response.
Gracefully falls back to a safe no-op tracer if Langfuse keys are absent or LANGFUSE_ENABLED=False.
"""

import logging
import uuid
from typing import Any, Dict, Optional

from backend.app.core.config import settings
from backend.app.observability.redaction import redact_secrets

logger = logging.getLogger("agentic_rag.tracing")

_langfuse_client = None


def get_langfuse_client():
    global _langfuse_client
    if not settings.LANGFUSE_ENABLED:
        return None
    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        return None

    if _langfuse_client is None:
        try:
            from langfuse import Langfuse
            _langfuse_client = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse client: {e}. Falling back to no-op tracer.")
            _langfuse_client = None
    return _langfuse_client


def trace_generation(
    name: str,
    model: str,
    input_data: Any,
    output_data: Any,
    usage: Optional[Dict[str, int]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    latency_ms: Optional[float] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """
    Records a generation in Langfuse with redacted inputs/outputs.
    Returns a trace_id string (either from Langfuse or generated locally).
    """
    clean_input = redact_secrets(input_data)
    clean_output = redact_secrets(output_data)
    clean_metadata = redact_secrets(metadata or {})

    client = get_langfuse_client()
    if client is None:
        # No-op trace id for audit logging
        local_trace_id = f"local-trace-{uuid.uuid4().hex[:12]}"
        logger.debug(f"[Trace No-Op] {name} (Model: {model}) -> Trace ID: {local_trace_id}")
        return local_trace_id

    try:
        trace = client.trace(
            name=name,
            user_id=str(user_id) if user_id else None,
            session_id=str(session_id) if session_id else None,
            metadata=clean_metadata,
        )

        trace.generation(
            name=name,
            model=model,
            input=clean_input,
            output=clean_output,
            usage=usage or {},
            metadata={
                **clean_metadata,
                "latency_ms": latency_ms,
            },
        )
        return trace.id
    except Exception as e:
        logger.warning(f"Error emitting trace to Langfuse: {e}")
        return f"err-trace-{uuid.uuid4().hex[:12]}"
