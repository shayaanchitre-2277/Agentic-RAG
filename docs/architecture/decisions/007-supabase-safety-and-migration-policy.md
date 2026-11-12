# 7. Local vs. Cloud Supabase Safety and Migration Policy

- **Status**: Accepted (Established)
- **Date**: 2026-11-11
- **Deciders**: Principal Software Architect, AI Systems Architect

## Context
During initial project setup, a local Supabase instance was initialized (`supabase init`), and a separate cloud Supabase project was created and linked (`supabase link`). Local Supabase and cloud Supabase represent completely distinct databases. If an automated script or agent inadvertently runs `supabase db push`, `supabase db reset --linked`, or commands with the `--linked` flag, production cloud state and schema could be irreversibly overwritten or wiped.

## Decision
We enforce strict local-first database operations and isolate cloud operations:
- **Strict Prohibition on Cloud Modification Commands**: Automated workflows, developer scripts, and AI agents are strictly forbidden from executing `supabase db push`, `supabase db reset --linked`, or any CLI command with the `--linked` flag.
- **Local-Only Development and Testing**: All schema migrations, RLS test suites, and application testing execute exclusively against the local Supabase instance running in Docker on `127.0.0.1:54321` / `54322`.
- **Manual, Human-Approved Cloud Migrations**: Deployment of migrations to the hosted cloud Supabase instance is restricted to Milestone M10.3 and must be executed manually by the human operator after explicit review.
- **Gitignore Cloud Pointer Artifacts**: Cloud-linking artifacts (such as `supabase/.temp/linked-project.json`) are permanently gitignored to prevent leaking cloud project identifiers into source control.

## Alternatives Considered
- **Direct Cloud Development**: Violates basic development hygiene, incurs live network latency for every test run, and creates high risk of data destruction during schema refactoring.
- **Automatic CI/CD Cloud Migrations**: High risk of unintended schema breakage during rapid early-phase prototyping.

## Consequences
- **Positive**: Complete safety against accidental cloud database destruction; local migrations are fast, fully reproducible, and testable offline.
- **Negative**: Requires manual synchronization step during final release (Phase 10).
