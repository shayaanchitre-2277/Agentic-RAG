# ==============================================================================
# Backend Dockerfile for Agentic RAG FastAPI
# Python 3.11 Slim Production Image
# ==============================================================================

FROM python:3.11-slim AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/backend \
    PORT=8000

# Create non-root application user
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application source code
COPY --chown=appuser:appgroup backend/app /app/backend/app
COPY --chown=appuser:appgroup backend/app /app/app

# Switch to non-root user
USER appuser

EXPOSE 8000

# Container healthcheck against /api/v1/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')" || exit 1

# Production server command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

