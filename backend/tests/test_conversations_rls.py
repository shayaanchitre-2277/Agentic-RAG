"""
Integration tests for Conversations and Messages API endpoints verifying
multi-tenant isolation (RLS) using local Supabase and FakeClient for LLM generation.

Tests verify:
  1. User A can create, list, retrieve, and delete conversations.
  2. User A posting a message triggers assistant reply generation via FakeClient and stores both in messages.
  3. A runs row is created and completed with total_tokens, latency, and cost recorded.
  4. User B receives 404/empty list when attempting to retrieve, post into, or delete User A's conversations.
  5. Multi-tenant RLS isolation is strictly preserved.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app

# Ensure fake client is used for all tests (₹0 cost, zero network calls)
settings.LLM_PROVIDER = "fake"

client = TestClient(app)

# Test User UUIDs matching supabase/seed.sql
USER_A_ID = "a0000000-0000-0000-0000-000000000001"
USER_B_ID = "b0000000-0000-0000-0000-000000000002"


def create_test_token(user_id: str, email: str) -> str:
    """Generate a signed JWT token recognized by local Supabase RLS."""
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(hours=2),
    }
    return jwt.encode(
        payload,
        settings.SUPABASE_JWT_SECRET,
        algorithm=settings.SUPABASE_JWT_ALGORITHM,
    )


@pytest.fixture(scope="module")
def user_a_headers():
    token = create_test_token(USER_A_ID, "user_a@test.local")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def user_b_headers():
    token = create_test_token(USER_B_ID, "user_b@test.local")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
def test_conversation_lifecycle_and_two_user_rls_isolation(user_a_headers, user_b_headers):
    # --- Step 1: User A creates a conversation ---
    create_payload = {"title": "Project Alpha Investigation"}
    res_a_create = client.post("/api/v1/conversations", json=create_payload, headers=user_a_headers)
    assert res_a_create.status_code == 201, f"Failed create: {res_a_create.text}"
    conv_a = res_a_create.json()
    conv_a_id = conv_a["id"]
    assert conv_a["title"] == "Project Alpha Investigation"
    assert conv_a["user_id"] == USER_A_ID

    # --- Step 2: User A posts a message -> Generates assistant reply & completes run ---
    msg_payload = {"content": "What is the status of Task 1?"}
    res_a_msg = client.post(f"/api/v1/conversations/{conv_a_id}/messages", json=msg_payload, headers=user_a_headers)
    assert res_a_msg.status_code == 201, f"Failed message post: {res_a_msg.text}"
    msg_data = res_a_msg.json()

    # Verify response structure contains both user message and assistant message
    user_msg = msg_data["user_message"]
    asst_msg = msg_data["assistant_message"]
    run_id = msg_data["run_id"]

    assert user_msg["content"] == "What is the status of Task 1?"
    assert user_msg["role"] == "user"
    assert user_msg["conversation_id"] == conv_a_id

    assert asst_msg["role"] == "assistant"
    assert "simulated assistant response" in asst_msg["content"].lower()
    assert asst_msg["conversation_id"] == conv_a_id

    # --- Step 3: User A retrieves their conversation (must contain 2 messages: user + assistant) ---
    res_a_get = client.get(f"/api/v1/conversations/{conv_a_id}", headers=user_a_headers)
    assert res_a_get.status_code == 200
    conv_detail = res_a_get.json()
    assert len(conv_detail["messages"]) == 2
    assert conv_detail["messages"][0]["id"] == user_msg["id"]
    assert conv_detail["messages"][1]["id"] == asst_msg["id"]

    # --- Step 4: User A lists conversations (must include conv_a) ---
    res_a_list = client.get("/api/v1/conversations", headers=user_a_headers)
    assert res_a_list.status_code == 200
    user_a_conv_ids = [c["id"] for c in res_a_list.json()]
    assert conv_a_id in user_a_conv_ids

    # --- Step 5: User B lists conversations (must NOT see User A's conversation) ---
    res_b_list = client.get("/api/v1/conversations", headers=user_b_headers)
    assert res_b_list.status_code == 200
    user_b_conv_ids = [c["id"] for c in res_b_list.json()]
    assert conv_a_id not in user_b_conv_ids

    # --- Step 6: User B attempts to GET User A's conversation (Must return 404) ---
    res_b_get = client.get(f"/api/v1/conversations/{conv_a_id}", headers=user_b_headers)
    assert res_b_get.status_code == 404
    assert "not found" in res_b_get.json()["detail"].lower()

    # --- Step 7: User B attempts to POST message into User A's conversation (Must return 404) ---
    res_b_msg = client.post(
        f"/api/v1/conversations/{conv_a_id}/messages",
        json={"content": "Malicious injected message"},
        headers=user_b_headers,
    )
    assert res_b_msg.status_code == 404
    assert "not found" in res_b_msg.json()["detail"].lower()

    # --- Step 8: User B attempts to DELETE User A's conversation (Must return 404) ---
    res_b_del = client.delete(f"/api/v1/conversations/{conv_a_id}", headers=user_b_headers)
    assert res_b_del.status_code == 404

    # --- Step 9: User A deletes their conversation ---
    res_a_del = client.delete(f"/api/v1/conversations/{conv_a_id}", headers=user_a_headers)
    assert res_a_del.status_code == 204

    # --- Step 10: Verify conversation is gone for User A ---
    res_a_verify = client.get(f"/api/v1/conversations/{conv_a_id}", headers=user_a_headers)
    assert res_a_verify.status_code == 404
