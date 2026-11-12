# 3. FastAPI as Thin API, SSE Streaming, and Python Logic Layer

- **Status**: Accepted (Established)
- **Date**: 2026-11-11
- **Deciders**: Principal Software Architect, AI Systems Architect

## Context
The system requires an HTTP API to serve client requests (React frontend), verify authentication tokens, trigger background graph runs, stream live progress to the UI via Server-Sent Events (SSE), and execute Python-based AI, ML, and connector logic.

## Decision
We use **FastAPI** as the backend API layer:
- **Thin Handlers**: FastAPI route handlers validate incoming request schemas (via Pydantic), verify JWT authenticity, persist initial conversation/run state, spawn the LangGraph workflow in the background, and return immediately.
- **No Orchestration in Handlers**: Route handlers must never become the orchestration engine or contain long-running agent logic.
- **Server-Sent Events (SSE)**: Execution events (`agent_events`) are streamed to the client over authenticated `GET /api/v1/runs/{id}/stream` endpoints.
- **Python Ecosystem**: FastAPI enables direct, zero-overhead access to Python libraries (LangGraph, CrewAI, Sentence Transformers, scikit-learn, XGBoost, PyTorch, spaCy).

## Alternatives Considered
- **Direct PostgREST / Supabase Edge Functions (Deno/TypeScript)**: Cannot run the required Python ML/NLP stack, Sentence Transformers, or native Python orchestration engines.
- **Django / Flask**: Heavier footprint with less modern native async support and automatic OpenAPI/Pydantic schema validation compared to FastAPI.

## Consequences
- **Positive**: High performance asynchronous request handling, automatic OpenAPI documentation, clean dependency injection (auth, db clients), and seamless Python AI/ML integration.
- **Negative**: Background execution lifecycle must be carefully managed to avoid orphaned tasks if the server restarts.
