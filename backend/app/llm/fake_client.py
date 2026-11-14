"""
Deterministic Fake LLM Client for offline, reproducible, ₹0 testing.
Simulates token counts and latency without making any network requests.
"""

import time

from backend.app.llm.base import LLMClient, LLMRequest, LLMResult
from backend.app.observability.tracing import trace_generation


class FakeClient(LLMClient):
    def __init__(self, fixed_response: str = "This is a simulated assistant response for testing."):
        self.fixed_response = fixed_response

    async def generate(self, request: LLMRequest) -> LLMResult:
        start_time = time.perf_counter()

        # Compute deterministic token counts based on word count
        all_text = " ".join(m.content for m in request.messages)
        input_tokens = max(1, len(all_text.split()))
        output_tokens = len(self.fixed_response.split())
        total_tokens = input_tokens + output_tokens

        latency_ms = (time.perf_counter() - start_time) * 1000

        model_name = request.model or "fake-model-v1"

        # Emit trace
        trace_id = trace_generation(
            name=f"llm_{request.role_name}",
            model=model_name,
            input_data=[m.model_dump() for m in request.messages],
            output_data=self.fixed_response,
            usage={
                "input": input_tokens,
                "output": output_tokens,
                "total": total_tokens,
            },
            metadata={"provider": "fake", "role": request.role_name},
            latency_ms=latency_ms,
            user_id=request.user_id,
            session_id=request.session_id,
        )

        return LLMResult(
            content=self.fixed_response,
            model=model_name,
            provider="fake",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=0.0,
            latency_ms=latency_ms,
            trace_id=trace_id,
        )
