# 1. Orchestration Separation: LangGraph Outer Spine and CrewAI Investigation Node

- **Status**: Accepted (Established)
- **Date**: 2026-11-11
- **Deciders**: Principal Software Architect, AI Systems Architect

## Context
We are building an AI investigative assistant that requires complex, multi-step investigation over live and historical project sources (Notion, Jira, Gmail, pgvector RAG). The system requires:
1. Global workflow determinism, step/token/cost budgets, retries, interrupts (human-in-the-loop approvals, clarification questions), state persistence, and resumable checkpoints.
2. Specialist, role-based multi-agent collaboration (Researcher, Analyst, Writer) during the actual evidence gathering and decomposition phase.

Conflating global workflow management and agent collaboration within a single framework leads to either uncontrollable delegation loops, opaque state transitions, or brittle custom graph execution.

## Decision
We enforce a strict separation of concerns:
- **LangGraph** owns the global state machine, deterministic control flow, budget enforcement, conditional branching, human-in-the-loop interrupts, retries, and persistence/checkpoints.
- **CrewAI** operates exclusively inside a single LangGraph node: the `investigate` node.
- Inside the `investigate` node, CrewAI orchestrates specialist agent roles using role-scoped, permission-checked tools.
- CrewAI autonomous agent delegation is disabled by default to prevent uncontrolled cost and step proliferation.
- CrewAI never makes global routing decisions, never directly writes to long-term memory tables, and never communicates directly with the client.

## Alternatives Considered
- **Pure LangGraph (no CrewAI)**: Would require manually writing low-level agent conversation loops and prompt handoffs. Viable, but misses CrewAI's high-level abstractions for role-based task execution and structured task outputs.
- **Pure CrewAI (no LangGraph)**: CrewAI does not offer first-class resumable state graphs, pause-and-resume interrupts for human approval, fine-grained cyclic graph guards, or native Postgres checkpointers required for robust production execution.
- **AutoGen / Semantic Kernel**: Adds unnecessary framework churn and lacks the deterministic state-graph guarantees provided by LangGraph.

## Consequences
- **Positive**: Clean separation of orchestration vs. role collaboration. Resumable execution and auditability at the graph level. Tight control over LLM token budgets.
- **Negative**: Requires mapping CrewAI structured outputs back into LangGraph state schemas. Requires two orchestration dependencies in the backend.

## Open Questions
- CrewAI LLM routing: Confirm in M3.2 whether CrewAI can be configured to invoke LLMs via our unified `LLMClient` or if it requires LiteLLM-compatible environment parameters.
