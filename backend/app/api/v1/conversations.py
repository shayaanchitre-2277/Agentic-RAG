"""
Conversation and message router implementing Phase 1 M1.3 endpoints.
All database access is performed via the user-scoped client dependency (get_user_db),
ensuring PostgreSQL RLS policies enforce multi-tenant isolation.
Assistant reply generation is traced through Langfuse and recorded in the runs table.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from backend.app.core.security import AuthenticatedUser, get_current_user
from backend.app.db.client import get_user_db
from backend.app.llm.base import LLMClient, LLMMessage, LLMRequest
from backend.app.llm.registry import get_llm_client
from backend.app.schemas.conversations import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    MessageCreate,
    MessagePostResponse,
    MessageResponse,
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create conversation",
)
def create_conversation(
    payload: ConversationCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Client = Depends(get_user_db),
):
    insert_data = {
        "user_id": str(current_user.user_id),
        "title": payload.title or "New Conversation",
    }
    res = db.table("conversations").insert(insert_data).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation",
        )
    return res.data[0]


@router.get(
    "",
    response_model=List[ConversationResponse],
    summary="List user conversations",
)
def list_conversations(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Client = Depends(get_user_db),
):
    # RLS restricts this to rows where user_id = auth.uid()
    res = (
        db.table("conversations")
        .select("*")
        .order("updated_at", desc=True)
        .execute()
    )
    return res.data or []


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation details and messages",
)
def get_conversation(
    conversation_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Client = Depends(get_user_db),
):
    # Fetch conversation (RLS filters out other users' conversations)
    conv_res = (
        db.table("conversations")
        .select("*")
        .eq("id", str(conversation_id))
        .execute()
    )
    if not conv_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    conv = conv_res.data[0]

    # Fetch messages for this conversation ordered chronologically
    msg_res = (
        db.table("messages")
        .select("*")
        .eq("conversation_id", str(conversation_id))
        .order("created_at", desc=False)
        .execute()
    )

    conv["messages"] = msg_res.data or []
    return conv


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete conversation",
)
def delete_conversation(
    conversation_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Client = Depends(get_user_db),
):
    # Verify existence and ownership under RLS
    check_res = (
        db.table("conversations")
        .select("id")
        .eq("id", str(conversation_id))
        .execute()
    )
    if not check_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    del_res = (
        db.table("conversations")
        .delete()
        .eq("id", str(conversation_id))
        .execute()
    )
    if not del_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return None


@router.post(
    "/{conversation_id}/messages",
    response_model=MessagePostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post message and generate assistant reply",
)
async def post_message(
    conversation_id: UUID,
    payload: MessageCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Client = Depends(get_user_db),
    llm: LLMClient = Depends(get_llm_client),
):
    # 1. Verify that the conversation exists and belongs to the authenticated user
    conv_res = (
        db.table("conversations")
        .select("id")
        .eq("id", str(conversation_id))
        .execute()
    )
    if not conv_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # 2. Store the user message (role="user")
    user_insert_data = {
        "conversation_id": str(conversation_id),
        "user_id": str(current_user.user_id),
        "role": "user",
        "content": payload.content,
    }
    user_msg_res = db.table("messages").insert(user_insert_data).execute()
    if not user_msg_res.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store user message",
        )
    user_message = user_msg_res.data[0]
    user_message_id = user_message["id"]

    # 3. Create a runs row (status="running", pipeline="walking_skeleton")
    run_insert_data = {
        "conversation_id": str(conversation_id),
        "message_id": user_message_id,
        "user_id": str(current_user.user_id),
        "pipeline": "walking_skeleton",
        "status": "running",
    }
    run_res = db.table("runs").insert(run_insert_data).execute()
    if not run_res.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize run state",
        )
    run_row = run_res.data[0]
    run_id = run_row["id"]

    # 4. Fetch recent conversation history (user-scoped) to construct context
    history_res = (
        db.table("messages")
        .select("role, content")
        .eq("conversation_id", str(conversation_id))
        .order("created_at", desc=False)
        .limit(20)
        .execute()
    )
    messages_history = [
        LLMMessage(role=m["role"], content=m["content"])
        for m in (history_res.data or [])
    ]

    # 5. Call LLM generate
    llm_request = LLMRequest(
        messages=messages_history,
        role_name="assistant",
        user_id=str(current_user.user_id),
        session_id=str(conversation_id),
    )

    try:
        llm_result = await llm.generate(llm_request)
    except Exception as exc:
        # On failure: update run status to failed with clean error message
        db.table("runs").update({
            "status": "failed",
            "error_message": str(exc),
            "completed_at": "now()",
        }).eq("id", run_id).execute()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM generation failed: {str(exc)}",
        ) from None

    # 6. Store assistant reply
    assistant_insert_data = {
        "conversation_id": str(conversation_id),
        "user_id": str(current_user.user_id),
        "role": "assistant",
        "content": llm_result.content,
    }
    asst_msg_res = db.table("messages").insert(assistant_insert_data).execute()
    if not asst_msg_res.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store assistant reply",
        )
    assistant_message = asst_msg_res.data[0]

    # 7. Update run to completed with token and cost metrics
    db.table("runs").update({
        "status": "completed",
        "total_tokens": llm_result.total_tokens,
        "estimated_cost_usd": llm_result.estimated_cost_usd,
        "latency_ms": int(llm_result.latency_ms),
        "completed_at": "now()",
    }).eq("id", run_id).execute()

    # 8. Touch conversation updated_at
    db.table("conversations").update({"updated_at": "now()"}).eq(
        "id", str(conversation_id)
    ).execute()

    return MessagePostResponse(
        user_message=user_message,
        assistant_message=assistant_message,
        run_id=UUID(run_id),
    )
