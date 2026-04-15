# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

Spec §11 Fase 1 (read-only) is implemented: 11 MCP tools covering company, invoices, contacts, accounts, account balances, balance sheet, and income statement. Fase 2 (journal/bank/transactions) and Fase 3 (writes with `confirm=True`) are not yet implemented. The spec (`fiken-mcp-spec.md`, Norwegian/nynorsk) remains the source of truth for intent — but two deviations are already baked in from live probing:

- **Pagination metadata lives in HTTP headers** (`Fiken-Api-Page`, `Fiken-Api-Page-Size`, `Fiken-Api-Result-Count`, `Fiken-Api-Page-Count`), not the body. `page` is 0-indexed. See `FikenClient.request_paginated()`.
- **`/balanceSheet/` and `/incomeStatements/` do not exist as API endpoints.** `fiken_balance_sheet` and `fiken_income_statement` are computed client-side from `/accountBalances` by aggregating account codes (1xxx/2xxx for balance; 3xxx-8xxx for income statement). Fiken does not auto-close P&L accounts annually, so a year-end `balance_check` equals cumulative unallocated result — this is expected.

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
