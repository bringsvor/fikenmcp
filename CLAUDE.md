# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

This repository currently contains only `fiken-mcp-spec.md` — a design spec (in Norwegian/nynorsk) for a Python MCP server that wraps Fiken's REST API v2. No implementation exists yet. The spec is the source of truth; read it before writing code.

## Planned stack

- Python 3.11+, packaged with `uv` (`uv sync`, `uv run python -m fiken_mcp.server`)
- `mcp` (Anthropic Python SDK), `httpx` (async), `pydantic-settings` for `.env` config
- Tests: `pytest` + `respx` for unit tests; `pytest -m integration` for demo-account tests

## Architecture (per spec §4, §7)

Target layout: `src/fiken_mcp/{server,client,config}.py` + `tools/{company,invoices,contacts,accounts,journal,bank,products,reports}.py`.

Critical design constraints:

- **Single `FikenClient` singleton** shared by all tools. It holds an `asyncio.Semaphore(1)` because Fiken allows only **1 concurrent request per user** — every HTTP call must go through the semaphore.
- **`companySlug` is auto-fetched** from `/user/` at startup and cached. Tools accept an override parameter but default to `FIKEN_COMPANY_SLUG`.
- **Bearer auth** via `FIKEN_API_TOKEN` env var. Base URL `https://api.fiken.no/api/v2`.
- **Retry policy**: 429 → exponential backoff, max 3 attempts. 401/400/404 → return structured error objects (not raised exceptions) as the MCP tool result.
- **Pagination**: list tools accept `page`/`pageSize` (default 25, max 100) and optional `fetch_all=True`; responses include `{data, total, page, pageSize}`.

## Write-operation safety (spec §6)

Every tool that mutates data (POST/PATCH/DELETE) **must** take `confirm: bool = False`. When `confirm=False`, return a human-readable summary of what *would* happen and do nothing. Only execute the API call when `confirm=True`. This is non-negotiable — the spec's whole write story depends on it.

## Tool naming

`fiken_{resource}_{operation}` (e.g. `fiken_invoices_list`, `fiken_invoice_create`). See spec §5 for the full inventory and implementation phases (§11: read-only first, writes last).

## Domain notes (Bringsvor-specific)

The spec calls out accounts like `2270` (marginlån), `2020` (aksjekapital/overkurs), `1920` (bank), and fritaksmetoden postings (8050/8060) as primary use cases. Balance-sheet and income-statement reports are the backbone for "kva er eigenkapitalen no?"-style questions.
