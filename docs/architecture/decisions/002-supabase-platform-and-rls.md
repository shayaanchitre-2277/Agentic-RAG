# 2. Supabase as Core Platform: Database, Auth, RLS, and pgvector

- **Status**: Accepted (Established)
- **Date**: 2026-11-11
- **Deciders**: Principal Software Architect, AI Systems Architect

## Context
The application requires secure multi-tenant isolation, user authentication, relational application storage, audit logging, vector embeddings storage, and similarity search for RAG. Managing separate standalone systems for authentication, relational storage, and a vector database increases operational complexity and data synchronization overhead.

## Decision
We adopt **Supabase** (PostgreSQL + PostgREST + Gotrue Auth + pgvector) as the unified backend data platform:
- **Authentication**: Supabase Auth (GoTrue) handles user identity, issuance of JWTs, and session lifecycle.
- **Relational Storage**: PostgreSQL holds conversations, messages, runs, tasks, agent executions, memory records, and audit logs.
- **Row Level Security (RLS)**: Enforces tenant isolation at the database layer. Every table in exposed schemas (`public`) mandates `user_id uuid NOT NULL DEFAULT auth.uid()` and RLS policies using `(SELECT auth.uid())`.
- **Vector Search**: PostgreSQL extension `pgvector` with HNSW indexing handles document embeddings (384-dimensional) and hybrid search (combining tsvector keyword matching via Reciprocal Rank Fusion).
- **Service Role Boundaries**: The `service_role` key is strictly forbidden in request-path code. Request-path operations execute under the authenticated user's JWT. Background workers access the database via a repository layer enforcing explicit `user_id` filtering.

## Alternatives Considered
- **Separate Vector DB (Pinecone / Qdrant / Weaviate) + Standalone PostgreSQL**: Increases latency, operational cost, and introduces cross-system transaction/consistency challenges.
- **Custom Auth (FastAPI OAuth2/JWT) + Vanilla PostgreSQL**: Reinvents user management, token rotation, and loses native integration with PostgreSQL RLS `auth.uid()`.

## Consequences
- **Positive**: Single unified database engine for metadata, relational entities, audit trails, and vector embeddings. Database-enforced multi-tenancy via RLS.
- **Negative**: Ties vector index performance to PostgreSQL resources; requires careful HNSW and GIN index tuning.
