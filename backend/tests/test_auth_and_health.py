"""
Unit tests for health endpoint and JWT authentication security dependency.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app

client = TestClient(app)


def test_health_endpoint_returns_200():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers


def test_missing_token_returns_401():
    response = client.get("/api/v1/conversations")
    assert response.status_code == 401
    assert "Missing authorization bearer token" in response.json()["detail"]


def test_malformed_token_returns_401():
    headers = {"Authorization": "Bearer not-a-valid-jwt-token"}
    response = client.get("/api/v1/conversations", headers=headers)
    assert response.status_code == 401
    assert "Invalid authentication token" in response.json()["detail"]


def test_expired_jwt_returns_401():
    expired_payload = {
        "sub": str(uuid4()),
        "email": "expired@test.local",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(
        expired_payload,
        settings.SUPABASE_JWT_SECRET,
        algorithm=settings.SUPABASE_JWT_ALGORITHM,
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/v1/conversations", headers=headers)
    assert response.status_code == 401
    assert "Token has expired" in response.json()["detail"]


def test_jwt_missing_sub_returns_401():
    bad_payload = {
        "email": "nosub@test.local",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    bad_token = jwt.encode(
        bad_payload,
        settings.SUPABASE_JWT_SECRET,
        algorithm=settings.SUPABASE_JWT_ALGORITHM,
    )
    headers = {"Authorization": f"Bearer {bad_token}"}
    response = client.get("/api/v1/conversations", headers=headers)
    assert response.status_code == 401
    assert "missing user identifier" in response.json()["detail"]


def test_cors_headers_for_allowed_origin():
    # Regular GET with allowed Origin
    response = client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"

    # Preflight OPTIONS request
    preflight = client.options(
        "/api/v1/conversations",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert preflight.headers.get("access-control-allow-credentials") == "true"

    # Disallowed origin
    bad_origin_res = client.get(
        "/api/v1/health",
        headers={"Origin": "http://unauthorized-domain.com"},
    )
    assert bad_origin_res.status_code == 200
    assert "access-control-allow-origin" not in bad_origin_res.headers
