# The Journey of a Message: Phase 1 Architecture Deep Dive

This document traces the complete lifecycle of a single prompt in the **Agentic RAG** system—from the moment an investigator types a query and clicks **Send** in the React frontend, through authentication, database row-level security isolation, LLM inference, and telemetry tracing.

---

## 1. End-to-End Architectural Flow Diagram

```text
+----------------+          +-------------------------+          +------------------------+
| React Frontend |          | Supabase Auth Service   |          | FastAPI Backend        |
|  (Chat UI)     |          | (Local / Cloud GoTrue)  |          | (App Entry / Router)   |
+--------+-------+          +------------+------------+          +-----------+------------+
         |                               |                                   |
         | 1. signInWithPassword()       |                                   |
         |------------------------------>|                                   |
         |    Returns JWT (Bearer)       |                                   |
         |<------------------------------|                                   |
         |                                                                   |
         | 2. POST /api/v1/conversations/{id}/messages (Bearer JWT)          |
         |------------------------------------------------------------------>|
         |                                                                   |
         |                                                       3. Verify JWT signature & claims
         |                                                          get_current_user(sub -> user_id)
         |                                                                   |
         |                                                       4. get_user_db(token)
         |                                                          PostgREST Client with user token
         |                                                                   |
         |                                   +-------------------------------+-------------------------------+
         |                                   |                                                               |
         |                       +-----------v-------------+                                     +-----------v-------------+
         |                       | Supabase Postgres (RLS) |                                     | LLM Client & Registry   |
         |                       | (conversations, msgs)   |                                     | (Gemini / Fake)         |
         |                       +-----------+-------------+                                     +-----------+-------------+
         |                                   |                                                               |
         |                                   | 5. INSERT INTO messages                                       |
         |                                   |    (role='user', auth.uid() enforced)                         |
         |                                   |                                                               |
         |                                   | 6. INSERT INTO runs (status='running')                        |
         |                                   |                                                               |
         |                                   |                                                   7. client.generate(req)
         |                                   |                                                      Wrapped in Langfuse
         |                                   |                                                      trace_generation()
         |                                   |                                                      + Secret Redaction
         |                                   |                                                               |
         |                                   |                                                   8. Result returned
         |                                   |                                                      (content, tokens, cost)
         |                                   |                                                               |
         |                                   | 9. INSERT INTO messages (role='assistant')                    |
         |                                   |    UPDATE runs (status='completed')                           |
         |                                   |                                                               |
         | 10. HTTP 200 MessagePostResponse  |<--------------------------------------------------------------+
         |<----------------------------------|
         | (user_message, assistant_message, run_id)
```

---

## 2. Technical Checkpoints

### Hop 1: Frontend State & JWT Attachment
- **Location**: `frontend/src/lib/api.ts` & `frontend/src/features/chat/ChatWorkspace.tsx`
- **Mechanism**:
  1. The user inputs text in the composer input and triggers `handleSend`.
  2. The frontend calls `supabase.auth.getSession()` to retrieve the current cryptographic session.
  3. The API client creates an HTTP `POST` request with the header: `Authorization: Bearer <access_token>`.
  4. Optimistic UI updates append a temporary message bubble immediately.

> 🧠 **Shayaan's Reflection Prompt 1: Browser Key Isolation**
> *Why is it critical that the frontend client only has access to `VITE_SUPABASE_ANON_KEY` and never the `SUPABASE_SERVICE_ROLE_KEY` or `GEMINI_API_KEY`? What attack vector does this protect against?*
>
> [YOUR EXPLANATION HERE]

---

### Hop 2: Network Boundary & CORS Inspection
- **Location**: `backend/app/main.py` (`CORSMiddleware`)
- **Mechanism**:
  1. The browser sends an `OPTIONS` preflight request verifying origin, headers (`Authorization`, `Content-Type`), and HTTP methods.
  2. FastAPI's `CORSMiddleware` checks the `Origin` header against `ALLOWED_ORIGINS` (`http://localhost:5173`, `http://127.0.0.1:5173`).
  3. If allowed, headers `Access-Control-Allow-Origin` and `Access-Control-Allow-Credentials: true` are returned.

---

### Hop 3: FastAPI Security Dependency (`get_current_user`)
- **Location**: `backend/app/core/security.py`
- **Mechanism**:
  1. The route handler declares `current_user: AuthenticatedUser = Depends(get_current_user)`.
  2. The dependency extracts the Bearer token from the `Authorization` header.
  3. It verifies the cryptographic signature (using `SUPABASE_JWT_SECRET` via HMAC-SHA256 or JWKS).
  4. It validates standard claims: expiration (`exp`), audience (`aud`), and extracts the subject (`sub`), representing the unique Postgres UUID of the user.

---

### Hop 4 & 5: Database Scoping & Row-Level Security (RLS)
- **Location**: `backend/app/db/client.py` & PostgreSQL schema (`supabase/migrations/`)
- **Mechanism**:
  1. The backend constructs a user-scoped client via `get_user_db(token)`.
  2. The PostgREST query sends the user's raw JWT to the database:
     `db.table("conversations").select("*").eq("id", conversation_id).execute()`
  3. In Postgres, PostgreSQL extracts `auth.uid()` from the JWT claims.
  4. The RLS policy evaluates:
     ```sql
     CREATE POLICY "Users can only access their own conversations"
     ON conversations FOR ALL
     USING (auth.uid() = user_id);
     ```
  5. If an attacker passes another user's conversation ID, Postgres returns zero rows (or denies insertion), preventing multi-tenant data leakage even if the backend application code had a bug.

> 🧠 **Shayaan's Reflection Prompt 2: RLS Defense-in-Depth**
> *Why do we enforce security at the database layer (PostgreSQL RLS) rather than relying solely on Python `if conversation.user_id == current_user.id:` checks?*
>
> [YOUR EXPLANATION HERE]

---

### Hop 6: LLM Provider Resolution & Execution
- **Location**: `backend/app/llm/` (`registry.py`, `fake_client.py`, `gemini_client.py`)
- **Mechanism**:
  1. Application code requests an LLM client via `get_llm_client()`.
  2. In development and CI environments, `LLM_PROVIDER=fake` provides `FakeClient`, delivering zero-cost deterministic responses without external network dependencies.
  3. In production, `GeminiClient` utilizes the Google GenAI SDK (`google-genai`) asynchronously, calculating token counts and financial cost tracking.

> 🧠 **Shayaan's Reflection Prompt 3: Provider Abstraction & Cost Guardrails**
> *How does decoupling the application router from specific LLM SDKs through `LLMClient` protect the project from vendor lock-in and accidental API billing during test runs?*
>
> [YOUR EXPLANATION HERE]

---

### Hop 7: Observability, Redaction & Audit Trail
- **Location**: `backend/app/observability/` (`redaction.py`, `tracing.py`) & `runs` table
- **Mechanism**:
  1. Before LLM requests and outputs are emitted to logs or Langfuse telemetry, `redact_secrets()` sanitizes Bearer tokens, Gemini keys, OpenAI keys, and Basic Auth patterns.
  2. `trace_generation` captures latency, token consumption, and model parameters. If Langfuse is unconfigured, it gracefully falls back to local tracking.
  3. A persistent audit row is maintained in the `runs` table (`pipeline='walking_skeleton'`, `status='completed'`).

> 🧠 **Shayaan's Reflection Prompt 4: Secret Sanitization Before Telemetry**
> *Why must secret scrubbing occur before sending data to external monitoring platforms like Langfuse? What risks exist if raw prompts containing user credentials reach third-party SaaS dashboards?*
>
> [YOUR EXPLANATION HERE]

---

### Hop 8: Response Delivery & UI Persistence
- **Location**: `backend/app/api/v1/conversations.py` -> `frontend/src/features/chat/ChatWorkspace.tsx`
- **Mechanism**:
  1. FastAPI returns `MessagePostResponse` containing:
     - `user_message`: Persisted database row for user query.
     - `assistant_message`: Persisted database row for assistant reply.
     - `run_id`: Audit UUID from `runs` table.
  2. The React frontend replaces the optimistic placeholder with the server-verified messages and scrolls to bottom.

