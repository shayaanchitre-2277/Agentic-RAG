# 6. Model Context Protocol (MCP) Integration Strategy

- **Status**: Accepted (Established)
- **Date**: 2026-11-11
- **Deciders**: Principal Software Architect, AI Systems Architect

## Context
The Model Context Protocol (MCP) provides an open standard for connecting AI applications to external tools and data sources. The project requirements mandate evaluating and incorporating MCP without introducing bloat, duplicating connector logic, or exposing the application to prompt-injection vulnerabilities via untrusted tool descriptions.

## Decision
We adopt a controlled, dual-backend connector strategy with strict security boundaries:
- **Direct REST API Connectors as Primary Baseline**: Native REST API connectors (implemented using parameterised templates with `httpx`) serve as the default, deterministic backend for Notion, Jira, and Gmail.
- **Dual-Backend Connector Interface**: All connectors implement a unified Python `Connector` interface (`health()`, `search()`, `get()`, `list_changes()`). A connector can be configured to execute via a direct API client or via an MCP client without altering agent code.
- **Single MCP Spike in Phase 4 (M4.5)**: One connector (e.g. Jira or Notion) will implement an MCP client backend using the official Python MCP SDK to benchmark against the direct REST API backend.
- **Security Boundaries**:
  - Tool descriptions from external or third-party MCP servers are treated as **untrusted data** and sanitized before injection into agent context.
  - Per-agent tool allow-lists are enforced; specialist analysts are restricted only to their authorized MCP tools.
  - Any MCP server must be pinned to an exact version and run in a network-constrained container.
  - MCP tools must be read-only; any write capabilities are disabled.
- **Custom MCP Server for `EvidenceItem`**: We will not expose our internal `EvidenceItem` database schema as a generic external MCP server unless an external consumer specifically requires it post-Phase 10.

## Alternatives Considered
- **MCP-Only Architecture (replacing all direct REST connectors)**: Introduces extra process-management overhead (running multiple local Node/Python MCP servers as sidecars), adds latency, and increases dependency risk.
- **No MCP**: Violates project architectural requirements and misses standard tooling interop.

## Consequences
- **Positive**: Clean abstraction allowing direct REST speed and reliability while validating MCP compatibility. Protects the core pipeline from external MCP outages or tool description injection.
- **Negative**: Requires maintaining two backend adapter implementations for the selected spike connector.
