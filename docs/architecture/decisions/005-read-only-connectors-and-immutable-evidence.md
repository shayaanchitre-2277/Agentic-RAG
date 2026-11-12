# 5. Read-Only Connectors and Immutable EvidenceItem Snapshots

- **Status**: Accepted (Established)
- **Date**: 2026-11-11
- **Deciders**: Principal Software Architect, AI Systems Architect

## Context
An investigative assistant must provide verifiable, provenance-backed claims across dynamic external systems (Notion, Jira, Gmail). External content constantly mutates, and LLMs risk citing volatile or unverified data. Additionally, granting write access to external corporate data creates severe security and accidental data modification risks.

## Decision
We enforce strict read-only connector boundaries and immutable evidence persistence:
- **Read-Only Access**: All external connectors (Notion, Jira, Gmail/Drive) operate exclusively with read-only scopes/permissions. No autonomous write actions are permitted anywhere in the agent investigation loop.
- **Normalized `EvidenceItem` Contract**: All connectors normalize external responses into a typed `EvidenceItem` Pydantic model carrying `source_id`, `external_id`, `url`, `content`, `source_updated_at`, `fetched_at`, and `trust_level` (`untrusted_content`).
- **Immutable Snapshots in `retrieved_items`**: Whenever an `EvidenceItem` is retrieved during a run, an immutable snapshot is written to the database table `retrieved_items`.
- **Append-Only Evidence Links**: Answers generate claim citations referencing immutable `retrieved_items.id` via `evidence_links`.
- **No In-Place Modification**: `retrieved_items` rows cannot be updated (`UPDATE` operations disallowed by policy). User-requested data deletions are handled through audited tombstones (`deleted_at`) or cascade from conversation deletion.

## Alternatives Considered
- **Direct Live Citations (URLs only)**: Fails when live content is updated, edited, or deleted after the answer is generated; provenance and historical auditability are lost.
- **Broad Read-Write API Scopes**: Unacceptable security risk; agents could accidentally alter project deadlines, close tickets, or draft unintended communications.

## Consequences
- **Positive**: Strict data integrity, total auditability of agent claims, immunity to post-investigation external data mutations, and protection against accidental external data loss.
- **Negative**: Increases database storage requirements to persist raw retrieved content snapshots.
