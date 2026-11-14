"""
FastAPI application entrypoint for Agentic RAG.
Configures:
  - Lifespan events
  - Request-ID tracking middleware
  - Safe structured logging with token/secret redaction
  - Uniform JSON error handlers
  - API v1 routers
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.conversations import router as conversations_router
from backend.app.api.v1.health import router as health_router
from backend.app.core.config import settings


# Custom Formatter that safely handles optional request_id
class RequestIdFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return super().format(record)


# Configure logging
handler = logging.StreamHandler()
handler.setFormatter(
    RequestIdFormatter(
        "%(asctime)s [%(levelname)s] [%(name)s] [ReqID: %(request_id)s] %(message)s"
    )
)

logging.basicConfig(level=settings.LOG_LEVEL, handlers=[handler])
logger = logging.getLogger("agentic_rag.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Agentic RAG FastAPI backend...", extra={"request_id": "startup"})
    yield
    logger.info("Shutting down Agentic RAG FastAPI backend...", extra={"request_id": "shutdown"})


app = FastAPI(
    title="Agentic RAG API",
    description="Backend API for Agentic RAG Investigative Assistant over Live Data & Persistent Memory",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# --- CORS Middleware (Local Frontend Origins) ---
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request ID & Logging Middleware ---

@app.middleware("http")
async def request_middleware(request: Request, call_next: Callable) -> Response:
    # Extract or generate a clean Request ID
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = req_id

    # Safe logging with token redaction
    auth_header = request.headers.get("Authorization", "")
    auth_status = "present (redacted)" if auth_header else "none"

    logger.info(
        f"Incoming {request.method} {request.url.path} (Auth: {auth_status})",
        extra={"request_id": req_id},
    )

    start_time = time.perf_counter()
    try:
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start_time) * 1000

        response.headers["X-Request-ID"] = req_id
        logger.info(
            f"Completed {request.method} {request.url.path} -> HTTP {response.status_code} in {latency_ms:.2f} ms",
            extra={"request_id": req_id},
        )
        return response
    except Exception as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(
            f"Unhandled server error on {request.method} {request.url.path} in {latency_ms:.2f} ms: {exc}",
            extra={"request_id": req_id},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred.",
                    "request_id": req_id,
                }
            },
            headers={"X-Request-ID": req_id},
        )


# --- Uniform Error Handlers ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", "-")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters or payload",
                "details": exc.errors(),
                "request_id": req_id,
            }
        },
        headers={"X-Request-ID": req_id},
    )


# --- Register Routers ---

app.include_router(health_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
