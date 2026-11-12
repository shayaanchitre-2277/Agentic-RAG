# 8. Virtual Environment Consistency: Root `.venv` Retention

- **Status**: Accepted (Established)
- **Date**: 2026-11-11
- **Deciders**: Principal Software Architect, AI Systems Architect

## Context
The original project roadmap and prompt templates mentioned an environment path of `backend\.venv`. However, the established local development environment was initialized at the project root: `E:\Agentic Rag\.venv`, configured with Python 3.11.9 and all verified Phase 0 dependencies (`google-auth`, `google-api-python-client`, `requests`, `python-dotenv`).

Relocating or creating a second virtual environment at this stage would introduce disk overhead, cause path drift with existing scripts, and potentially break PowerShell session setups.

## Decision
We retain the existing single root virtual environment:
- **Location**: `E:\Agentic Rag\.venv` (Python 3.11.9).
- **Environment Setup**: The session script `scripts/dev/env.ps1` explicitly activates `E:\Agentic Rag\.venv`.
- **Packaging Strategy**: When the `backend/` folder structure is established in Phase 1, backend scripts and modules will continue utilizing the root virtual environment. A separate nested `backend\.venv` will NOT be created.
- **Git Hygiene**: `.gitignore` explicitly excludes `.venv/` at the root as well as `backend/.venv/` to prevent accidental commits under any directory structure.

## Alternatives Considered
- **Migrating to `backend\.venv` now**: Requires re-installing all packages, breaking existing PowerShell path references, and risking dependency discrepancies.
- **Dual Virtual Environments**: Wasteful, confusing, and prone to "works in one venv, fails in another" bugs.

## Consequences
- **Positive**: Zero disruption to working spikes, stable PowerShell development workflows, saves disk space on `E:`.
- **Negative**: Deviates slightly from the original textual prompt template, but this is explicitly documented and aligned.
