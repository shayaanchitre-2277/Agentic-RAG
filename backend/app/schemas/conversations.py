"""
Pydantic v2 schemas for Conversations and Messages.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# --- Message Schemas ---

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Text content of the message")


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    user_id: UUID
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


# --- Conversation Schemas ---

class ConversationCreate(BaseModel):
    title: Optional[str] = Field("New Conversation", max_length=255, description="Conversation title")


class ConversationUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Updated conversation title")


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = Field(default_factory=list)
