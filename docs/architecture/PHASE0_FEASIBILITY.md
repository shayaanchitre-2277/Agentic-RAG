# Phase 0 Feasibility and Verification Matrix

This document tracks all external integrations, architectural decisions, and technical assumptions investigated during **Phase 0: Unknowns, accounts, sandboxes and connectivity spikes**.

---

## 1. Feasibility Matrix

| Integration / Decision | Current Status | Verification Performed | Result | Missing Work | Fallback |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Notion** | COMPLETED | Executed `scripts/spikes/notion_spike.py` using live API key and test query for 'Agentic RAG Sandbox'. | **SUCCESS**: Retrieved page `412880dc-e268-805b-944b-faf90b5e5418` and block contents (Status, Deadline, Tasks). | None for spike. In Phase 4, build parameterized query templates and change-log db integration. | Mock connector / local JSON dump. |
| **Gmail** | COMPLETED | Executed `scripts/spikes/gmail_spike.py` with scope `gmail.readonly`. Verified `credentials/token.json` refresh & retrieval. | **SUCCESS**: Granted scope `['https://www.googleapis.com/auth/gmail.readonly']`. Retrieved message headers (Date, From, Subject) cleanly with zero body exposure. | In Phase 4, build connector query interface (search by project aliases & time window) and token refresh handler. | Fall back to Google Drive read-only or mocked mailbox data. |
| **Jira** | NOT STARTED | Checked `.env` and scripts. | **NOT TESTED**: No Jira API token, sandbox URL, or spike script present. | Create Jira free cloud instance, populate tasks & blockers, add `JIRA_API_TOKEN` & `JIRA_BASE_URL` to `.env`, write `jira_spike.py`. | Mock Jira connector or GitHub Issues as fallback blocker source. |
| **Gemini API** | NOT STARTED | Checked `.env` and dependencies. | **NOT TESTED**: No `GEMINI_API_KEY` present in `.env`. | Add `GEMINI_API_KEY` to `.env` and execute minimal text generation spike using `google-genai` SDK. | Fallback to OpenAI API as primary if Gemini unavailable. |
| **OpenAI API** | NOT STARTED | Checked `.env`. | **NOT TESTED**: No `OPENAI_API_KEY` present in `.env`. | Add `OPENAI_API_KEY` to `.env` and execute minimal test call. | Gemini or local Ollama for secondary/judge role. |
| **Hugging Face** | NOT STARTED | Checked environment variables and scripts. | **NOT TESTED**: `HF_TOKEN` not configured; cache directory configured via `env.ps1`. | Add read-only HF token to `.env`, set `HF_HOME=E:\Agentic Rag\.cache\huggingface`. | Public models downloaded directly without token. |
| **Supabase JWT Signing** | PARTIALLY COMPLETED | Inspected `supabase/config.toml` and local setup. Verified local CLI configuration. | **PARTIAL**: Local Supabase configured with standard JWT secret in `config.toml`. Cloud project linked (`linked-project.json`). Cloud JWKS vs shared secret not yet verified live. | Verify whether the linked cloud project uses RS256/asymmetric JWKS or HS256 shared secret. | Configurable JWT verification dependency in FastAPI (JWKS or HS256). |
| **Embedding Model** | DECIDED (Pending Spike) | Evaluated dimension constraints and blueprint recommendations. | **RECOMMENDED**: BGE-small-en-v1.5 or all-MiniLM-L6-v2 (384-dimensional). Matches `vector(384)` in schema. | Implement embedding spike verifying latency and memory footprint on E: cache. | Fall back to `sentence-transformers/all-MiniLM-L6-v2`. |
| **MCP Server Options** | NOT STARTED | Researched available MCP servers for Notion/Jira/Gmail. | **NOT TESTED**: Survey of official and community MCP servers not finalized. | Evaluate official Model Context Protocol servers vs direct REST API connectors. | Direct REST API connectors remain primary; MCP as optional secondary adapter. |
| **CrewAI LLM Routing Feasibility** | NOT STARTED | Checked dependencies. CrewAI not yet installed in `.venv`. | **NOT TESTED**: CrewAI provider integration and LiteLLM bypass need verification in M3.2. | Test initializing CrewAI Agent using custom LLM wrapper in Phase 3. | Configure CrewAI via standard LiteLLM environment variables matching LLMClient. |
| **LangGraph / Postgres Checkpointer on Windows** | NOT STARTED | Inspected platform requirements and Windows event loop constraints. | **NOT TESTED**: Windows event loop (`WindowsSelectorEventLoopPolicy`) needed for async psycopg. | Spike `asyncpg` / `psycopg` connection on Windows in M5.1. | Use synchronous checkpointer or explicit `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())`. |

---

## 2. Detailed Technical Findings & Milestone Progress

### M0.2 Repository Hygiene Status: COMPLETED
1. **Git Initialization**: Repository initialized at `E:\Agentic Rag`. Verified via `git rev-parse --show-toplevel`. No commits made pending user review.
2. **Line Endings (`.gitattributes`)**: Configured `* text=auto eol=lf` across standard text/source files, with explicit `crlf` preservation for Windows PowerShell scripts (`.ps1`, `.bat`, `.cmd`).
3. **Environment Template (`.env.example`)**: Created comprehensive placeholder template with zero secrets, documenting all Phase 0-4 environment variables.
4. **Environment Setup Script (`scripts/dev/env.ps1`)**: Created and verified session-level setup script targeting E: drive cache directories (`.cache/huggingface`, `.cache/pip`, `.npm-cache`, `.cache/torch`, `.tmp`) and activating the root `.venv`.
5. **Security Audit (`.gitignore`)**: Hardened `.gitignore` to explicitly ignore `.env`, `.venv`, `credentials/` (including `gmail_oauth_client.json` and `token.json`), temporary files, node modules, and Supabase ephemeral cache (`supabase/.temp/`, `supabase/.branches/`). Tested via `git check-ignore`.

### Virtual Environment Architecture Note
- **Discrepancy Documented**: The original project plan referenced `backend\.venv`. The existing development environment utilizes a single root-level `.venv` (`E:\Agentic Rag\.venv`) running **Python 3.11.9**.
- **Decision**: To avoid unnecessary duplication, disk overhead, or path breakage, the root `.venv` is retained for all Phase 0 development. Any future sub-package separation will be addressed during Phase 1 packaging without moving the current functional environment.

### Notion Live Spike (M0.3)
- **Script**: `scripts/spikes/notion_spike.py`
- **Result**: Successfully connected using `NOTION_API_KEY`.
- **Returned Page**:
  - Title/Query: "Agentic RAG Sandbox"
  - Page ID: `412880dc-e268-805b-944b-faf90b5e5418`
  - Blocks: Project name, status (Phase 0), next task, deadline (15 November 2026).
- **Status**: **PASSED**.

### Gmail Read-Only Spike (M0.3)
- **Script**: `scripts/spikes/gmail_spike.py`
- **Result**: Successfully authenticated via OAuth 2.0 with granted scope `['https://www.googleapis.com/auth/gmail.readonly']`.
- **Verified Behavior**:
  - Retrieved 5 email metadata records (Date, From, Subject) cleanly.
  - Full email bodies strictly protected and not fetched.
  - OAuth token caching verified: Token cached in `credentials/token.json` and automatically refreshed without user intervention.
- **Status**: **PASSED**.
