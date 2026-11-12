"""
Health check router.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Service Health Check")
def get_health():
    return {"status": "ok"}
