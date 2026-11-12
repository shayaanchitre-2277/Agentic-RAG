# Phase 0 Feasibility and Verification Matrix

This document tracks all external integrations, architectural decisions, and technical assumptions investigated during **Phase 0: Unknowns, accounts, sandboxes and connectivity spikes**.

---

## 1. Feasibility Matrix

| Integration / Decision | Current Status | Verification Performed | Result | Missing Work | Fallback |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Notion** | COMPLETED | Executed `scripts/spikes/notion_spike.py` using live API key and test query for 'Agentic RAG Sandbox'. | **SUCCESS**: Retrieved page `412880dc-e268-805b-944b-faf90b5e5418` and block contents (Status, Deadline, Tasks). | None for spike. In Phase 4, build parameterized query templates and change-log db integration. | Mock connector / local JSON dump. |
| **Gmail** | COMPLETED | Executed `scripts/spikes/gmail_spike.py` with scope `gmail.readonly`. Verified `credentials/token.json` refresh & retrieval. | **SUCCESS**: Granted scope `['https://www.googleapis.com/auth/gmail.readonly']`. Retrieved 5 message headers (Date, From, Subject) cleanly with zero body exposure. | In Phase 4, build connector query interface (search by project aliases & time window) and token refresh handler. | Fall back to Google Drive read-only or mocked mailbox data. |
| **Jira** | COMPLETED | Executed `scripts/spikes/jira_spike.py` using Atlassian Classic API Token via HTTP Basic Authentication against `https://shayaanchitre.atlassian.net`. Verified `/rest/api/3/myself`, `/rest/api/3/project`, and `/rest/api/3/search/jql`. | **ALL CHECKS PASSED (HTTP 200)**: Authenticated as 'Shayaan Chitre' (273 ms), retrieved project `[SCRUM] My Software Team` (226 ms), and retrieved 4 issues via `/search/jql` with statuses and issue links (344 ms). | In Phase 4, implement Jira connector with parameterised JQL templates and blocker detection (`issuelinks`). | Mock Jira connector or GitHub Issues. |
| **Gemini API** | COMPLETED | Executed `scripts/spikes/gemini_spike.py` using `google-genai` SDK v3.1.0 with model `gemini-3.8-flash`. | **SUCCESS**: Authenticated and received valid generation response (`OK`). | In Phase 1/3, implement `GeminiClient` adapter under `LLMClient` interface and configure roles in `models.yaml`. | Fallback to OpenAI API as primary if Gemini unavailable. |
| **OpenAI API** | BLOCKED (Insufficient Quota) | Executed `scripts/spikes/openai_spike.py` using `openai` SDK v3.49.0 targeting `gpt-4o-mini`. | **AUTH PASSED / 429 QUOTA**: API key is valid and authenticated, but account has zero credits remaining (`Error code: 429 - You have no credits remaining`). | User to add credits to the OpenAI account billing settings. Once funded, rerun `openai_spike.py`. | Gemini or local Ollama model for secondary/judge role if OpenAI is not funded. |
| **Hugging Face** | BLOCKED (Token Missing; Public Ready) | Checked `.env` and cache settings. `HF_TOKEN` is absent. `env.ps1` sets `HF_HOME=E:\Agentic Rag\.cache\huggingface`. | **FEASIBLE WITHOUT TOKEN**: Public model downloads (e.g. Sentence Transformers `all-MiniLM-L6-v2`) do NOT require authentication. Token is only required for gated/private models or Hub upload. | Optional: User to add `HF_TOKEN` to `.env` if using gated models or push-to-hub workflows. | Public Hugging Face Hub downloads without authentication. |
| **Supabase JWT Signing** | PARTIALLY COMPLETED | Inspected `supabase/config.toml` and local setup. Verified local CLI configuration. | **PARTIAL**: Local Supabase configured with standard JWT secret in `config.toml`. Cloud project linked (`linked-project.json`). Cloud JWKS vs shared secret not yet verified live. | Verify whether the linked cloud project uses RS256/asymmetric JWKS or HS256 shared secret. | Configurable JWT verification dependency in FastAPI (JWKS or HS256). |
| **Embedding Model** | DECIDED (Pending Spike) | Evaluated dimension constraints and blueprint recommendations. | **RECOMMENDED**: BGE-small-en-v1.5 or all-MiniLM-L6-v2 (384-dimensional). Matches `vector(384)` in schema. | Implement embedding spike verifying latency and memory footprint on E: cache. | Fall back to `sentence-transformers/all-MiniLM-L6-v2`. |
| **MCP Server Options** | COMPLETED (Surveyed) | Evaluated MCP host, client, server models, security risks, and dual-backend architecture. | **FEASIBLE**: Direct REST API connectors as primary baseline. Phase 4 (M4.5) implements one MCP client backend for comparison. ADR 006 documented. | Implement single connector MCP backend in M4.5. | Direct REST API connectors remain primary baseline. |
| **CrewAI LLM Routing Feasibility** | DECIDED (Pending M3.2) | Inspected CrewAI and LLM provider architecture. | **DECIDED**: ADR 001 establishes CrewAI inside `investigate` node. ADR 004 establishes provider registry. | Verify custom `LLMClient` injection into CrewAI agents in M3.2. | LiteLLM environment configuration matching registry. |
| **LangGraph / Postgres Checkpointer on Windows** | DECIDED (Pending M5.1) | Inspected platform requirements and Windows event loop constraints. | **DECIDED**: Windows event loop (`WindowsSelectorEventLoopPolicy`) needed for async psycopg. | Spike `asyncpg` / `psycopg` connection on Windows in M5.1. | Use synchronous checkpointer or explicit `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())`. |

---

## 2. Detailed Technical Findings & Milestone Progress

### M0.2 Repository Hygiene Status: COMPLETED
1. **Git Initialization**: Repository initialized at `E:\Agentic Rag` (commit `5a2e6da`).
2. **Line Endings (`.gitattributes`)**: Configured `* text=auto eol=lf` across standard text/source files, with explicit `crlf` preservation for Windows PowerShell scripts (`.ps1`, `.bat`, `.cmd`).
3. **Environment Template (`.env.example`)**: Created comprehensive placeholder template with zero secrets, documenting all Phase 0-4 environment variables.
4. **Environment Setup Script (`scripts/dev/env.ps1`)**: Created and verified session-level setup script targeting E: drive cache directories (`.cache/huggingface`, `.cache/pip`, `.npm-cache`, `.cache/torch`, `.tmp`) and activating the root `.venv`.
5. **Security Audit (`.gitignore`)**: Hardened `.gitignore` to explicitly ignore `.env`, `.venv`, `credentials/` (including `gmail_oauth_client.json` and `token.json`), temporary files, node modules, and Supabase ephemeral cache (`supabase/.temp/`, `supabase/.branches/`). Tested via `git check-ignore`.

### Virtual Environment Architecture Note (ADR 008)
- **Discrepancy Documented**: The original project plan referenced `backend\.venv`. The existing development environment utilizes a single root-level `.venv` (`E:\Agentic Rag\.venv`) running **Python 3.11.9**.
- **Decision**: Retain root `.venv` to prevent path fragmentation and overhead (ADR 008).

### Jira Cloud Classic API Token Spike (M0.3)
- **Script**: `scripts/spikes/jira_spike.py`
- **Target Host**: `https://shayaanchitre.atlassian.net`
- **Authentication**: HTTP Basic Auth (`JIRA_USER_EMAIL` + Classic `JIRA_API_TOKEN`)
- **Results by Endpoint**:
  - `GET /rest/api/3/myself`: **SUCCESS (HTTP 200)** in 273 ms. Authenticated as `'Shayaan Chitre'` (`accountId: 712020:01a13638-0097-4282-8717-c4dd40e57e60`, Active: `True`).
  - `GET /rest/api/3/project`: **SUCCESS (HTTP 200)** in 226 ms. Retrieved accessible project: `[SCRUM] My Software Team` (`ID: 10000`).
  - `GET /rest/api/3/search/jql`: **SUCCESS (HTTP 200)** in 344 ms. Bounded query (`project is not EMPTY ORDER BY updated DESC`, `maxResults=5`, `fields="key,summary,status,issuelinks,updated"`) retrieved 4 issues (`SCRUM-2`, `SCRUM-1`, `SCRUM-4`, `SCRUM-3`) with full statuses and issue-link structures.
- **Status**: **COMPLETED (ALL CHECKS PASSED)**. Classic API Token authentication against Jira Cloud REST API v3 is fully verified for read-only user, project, and issue/blocker retrieval.

### Notion Live Spike (M0.3)
- **Script**: `scripts/spikes/notion_spike.py`
- **Result**: Successfully connected using `NOTION_API_KEY`.
- **Returned Page**:
  - Title/Query: "Agentic RAG Sandbox"
  - Page ID: `412880dc-e268-805b-944b-faf90b5e5418`
  - Blocks: Project name, status (Phase 0), next task, deadline (15 November 2026).
- **Status**: **PASSED**.

### Gemini API Spike (M0.3)
- **Script**: `scripts/spikes/gemini_spike.py`
- **SDK**: `google-genai` version 3.1.0
- **Model**: `gemini-3.8-flash`
- **Result**: Authenticated via `GEMINI_API_KEY` and generated expected response (`OK`).
- **Status**: **PASSED**.

### OpenAI API Spike (M0.3)
- **Script**: `scripts/spikes/openai_spike.py`
- **SDK**: `openai` version 3.49.0
- **Model**: `gpt-4o-mini`
- **Result**: Authentication handshake succeeded, but request failed with **HTTP 429**: *"You have no credits remaining. Add credits to continue using the API at https://platform.openai.com/settings/organization/billing/."*
- **Status**: **BLOCKED (Insufficient Quota)**. Requires billing credits to be added to the OpenAI organization.

### Gmail Read-Only Spike (M0.3)
- **Script**: `scripts/spikes/gmail_spike.py`
- **Result**: Successfully authenticated via OAuth 2.0 with granted scope `['https://www.googleapis.com/auth/gmail.readonly']`.
- **Verified Behavior**:
  - Retrieved 5 email metadata records (Date, From, Subject) cleanly.
  - Full email bodies strictly protected and not fetched.
  - OAuth token caching verified: Token cached in `credentials/token.json` and refreshed cleanly.
- **Status**: **PASSED**.

### MCP Survey Summary (M0.3 & ADR 006)
- **Protocol Evaluation**: Evaluated MCP Client/Server model. Direct REST connectors (via `httpx`) will serve as the primary deterministic pipeline.
- **Security & Hygiene**: External tool descriptions from MCP servers will be treated as untrusted input to defend against prompt injection. Per-agent tool allow-lists will be enforced.
- **Implementation Strategy**: One connector (Jira or Notion) will implement an optional secondary MCP backend in Phase 4 (M4.5) to benchmark latency and reliability against the direct REST implementation.

### Architecture Decision Records Created (docs/architecture/decisions/)
1. `001-orchestration-separation.md`: LangGraph outer spine, CrewAI inside investigate node.
2. `002-supabase-platform-and-rls.md`: Supabase Postgres, Auth, RLS, and pgvector.
3. `003-fastapi-backend-layer.md`: FastAPI thin routes, SSE streaming, and Python runtime.
4. `004-llm-provider-strategy.md`: Gemini primary, OpenAI secondary/judge, role-based model registry.
5. `005-read-only-connectors-and-immutable-evidence.md`: Read-only scopes, EvidenceItem contract, immutable retrieved_items.
6. `006-mcp-integration-strategy.md`: Direct REST baseline, dual-backend abstraction, single MCP comparison in M4.5.
7. `007-supabase-safety-and-migration-policy.md`: Local-only development, prohibition of automated cloud pushes.
8. `008-root-venv-retention.md`: Retention of root `E:\Agentic Rag\.venv` for stability.
