"""
Core Pydantic models and Abstract Base Class for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


class LLMMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class LLMRequest(BaseModel):
    messages: List[LLMMessage]
    role_name: str = Field(default="assistant", description="Agent or functional role name (e.g. planner, researcher, judge)")
    model: Optional[str] = Field(default=None, description="Optional override for model ID")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class LLMResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0
    trace_id: Optional[str] = None


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResult:
        """Execute a text generation call asynchronously and return structured LLMResult."""
        pass
