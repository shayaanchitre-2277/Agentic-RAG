# 4. Multi-Provider LLM Strategy: Gemini Primary and OpenAI Secondary/Judge

- **Status**: Accepted (Established)
- **Date**: 2026-11-11
- **Deciders**: Principal Software Architect, AI Systems Architect

## Context
Relying on a single LLM vendor introduces single-point-of-failure risks, rate-limit vulnerabilities, and evaluation bias (e.g., an LLM acting as a judge of its own generated answers tends to score itself higher). The architecture requires primary high-throughput generation and a distinct secondary model for evaluation, claim verification, and judge tasks.

## Decision
We establish a multi-provider strategy behind a unified `LLMClient` interface:
- **Gemini (Primary Provider)**: Powers high-volume, multi-turn reasoning, planning, and agent synthesis roles via the official Google GenAI SDK.
- **OpenAI (Secondary / Judge Provider)**: Powers the independent citation verification, claim support judging, and benchmark evaluation harness to avoid self-evaluation bias.
- **Role-Based Model Registry**: Application code never references raw model strings directly. Components request models by functional role (`planner`, `researcher`, `synthesizer`, `verifier`, `judge`) from `models.yaml`.
- **Enforced Model Separation**: The system emits a configuration warning/error if the `synthesizer` and `judge` resolve to the identical model identifier during citation checking.

## Alternatives Considered
- **Single Vendor (Gemini-only or OpenAI-only)**: Vulnerable to vendor outages, rate limits, and compromises evaluation objectivity.
- **LiteLLM as Mandatory Production Dependency**: LiteLLM adds extra dependencies and abstraction overhead. We implement a lightweight internal `LLMClient` adapter pattern, using LiteLLM only if strictly demanded by CrewAI.

## Consequences
- **Positive**: Resilient architecture, eliminates evaluation bias, allows cost/latency optimization per agent role.
- **Negative**: Requires managing two vendor API keys and monitoring differences in token pricing and structured output formats.
