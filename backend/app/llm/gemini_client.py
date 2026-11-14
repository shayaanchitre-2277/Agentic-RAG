"""
Gemini LLM Client wrapping the official google-genai SDK.
Handles model execution, latency tracking, token usage extraction,
cost estimation, and Langfuse tracing.
"""

import time
from typing import Optional

from backend.app.core.config import settings
from backend.app.llm.base import LLMClient, LLMRequest, LLMResult
from backend.app.observability.tracing import trace_generation

# Standard pricing for gemini-3.8-flash (per million tokens)
# Input: $0.10 / 1M tokens ($0.00000010 per token)
# Output: $0.40 / 1M tokens ($0.00000040 per token)
GEMINI_FLASH_INPUT_COST = 0.10 / 1_000_000
GEMINI_FLASH_OUTPUT_COST = 0.40 / 1_000_000


class GeminiClient(LLMClient):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in environment or settings.")

        from google import genai
        self.client = genai.Client(api_key=self.api_key)

    async def generate(self, request: LLMRequest) -> LLMResult:
        model_name = request.model or settings.GEMINI_DEFAULT_MODEL

        # Convert messages into prompt format
        # System instructions separated if present
        system_instruction = None
        contents = []

        for m in request.messages:
            if m.role == "system":
                system_instruction = m.content
            else:
                contents.append(f"{m.role.capitalize()}: {m.content}")

        prompt_str = "\n\n".join(contents)

        start_time = time.perf_counter()

        from google.genai import types
        config = types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            system_instruction=system_instruction,
        )

        try:
            # Note: google-genai client has async support via client.aio
            if hasattr(self.client, "aio"):
                response = await self.client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt_str,
                    config=config,
                )
            else:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt_str,
                    config=config,
                )

            latency_ms = (time.perf_counter() - start_time) * 1000

            text_content = response.text.strip() if response.text else ""

            # Extract token metadata if available
            usage_meta = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else len(prompt_str.split())
            output_tokens = getattr(usage_meta, "candidates_token_count", 0) if usage_meta else len(text_content.split())
            total_tokens = getattr(usage_meta, "total_token_count", input_tokens + output_tokens) if usage_meta else (input_tokens + output_tokens)

            cost_usd = (input_tokens * GEMINI_FLASH_INPUT_COST) + (output_tokens * GEMINI_FLASH_OUTPUT_COST)

            # Emit trace
            trace_id = trace_generation(
                name=f"llm_{request.role_name}",
                model=model_name,
                input_data=[m.model_dump() for m in request.messages],
                output_data=text_content,
                usage={
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens,
                },
                metadata={
                    "provider": "gemini",
                    "role": request.role_name,
                    "cost_usd": cost_usd,
                },
                latency_ms=latency_ms,
                user_id=request.user_id,
                session_id=request.session_id,
            )

            return LLMResult(
                content=text_content,
                model=model_name,
                provider="gemini",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=round(cost_usd, 6),
                latency_ms=round(latency_ms, 2),
                trace_id=trace_id,
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            # Redact any accidental keys in error messages
            clean_err = str(e)
            if self.api_key and self.api_key in clean_err:
                clean_err = clean_err.replace(self.api_key, "[REDACTED_API_KEY]")
            raise RuntimeError(f"Gemini API error after {latency_ms:.2f} ms: {clean_err}") from None
