"""
Authentication dependencies and JWT verification.
Supports:
  - HS256 shared secret verification
  - Asymmetric RS256 via JWKS (if SUPABASE_JWKS_URL is provided)
Returns typed AuthenticatedUser model. Raises HTTP 401 on missing, invalid, or expired tokens.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.config import settings

# HTTPBearer extracts 'Authorization: Bearer <token>'
security_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    user_id: UUID
    email: Optional[str]
    raw_token: str


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> AuthenticatedUser:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_token = credentials.credentials

    try:
        # Determine verification key & algorithm
        if settings.SUPABASE_JWKS_URL:
            jwks_client = jwt.PyJWKClient(settings.SUPABASE_JWKS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(raw_token)
            payload = jwt.decode(
                raw_token,
                signing_key.key,
                algorithms=[settings.SUPABASE_JWT_ALGORITHM, "RS256"],
                options={"verify_aud": False},
            )
        else:
            if not settings.SUPABASE_JWT_SECRET:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Server authentication configuration error: JWT secret missing",
                )
            payload = jwt.decode(
                raw_token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=[settings.SUPABASE_JWT_ALGORITHM],
                options={"verify_aud": False},
            )

        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims: missing user identifier ('sub')",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            user_uuid = UUID(sub)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims: 'sub' is not a valid UUID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        email = payload.get("email")

        return AuthenticatedUser(
            user_id=user_uuid,
            email=email,
            raw_token=raw_token,
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
