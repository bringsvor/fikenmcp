# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

Spec §11 Fase 1, Fase 2 (read-only), and Fase 3 (writes) are implemented, plus extensions: **33 MCP tools** with **85 tests**. Every write tool (`*_create`, `*_update`, `*_send`, `*_attachment_add`) defaults to `confirm=False` and returns a structured dry-run summary; the API call only happens on `confirm=True` (spec §6). Extensions beyond original spec: purchases, products (CRUD), inbox, attachments (invoice + journal entry, multipart/base64). The spec (`fiken-mcp-spec.md`, Norwegian/nynorsk) remains the source of truth for intent — but several deviations are baked in from live probing.

## Fiken API v2 gotchas (from empirical testing)

- **Pagination metadata lives in HTTP headers** (`Fiken-Api-Page`, `Fiken-Api-Page-Size`, `Fiken-Api-Result-Count`, `Fiken-Api-Page-Count`), not the body. `page` is 0-indexed. See `FikenClient.request_paginated()`.
- **`/balanceSheet/` and `/incomeStatements/` do not exist.** `fiken_balance_sheet` and `fiken_income_statement` are computed client-side from `/accountBalances` by aggregating account codes (1xxx/2xxx for balance; 3xxx-8xxx for income statement). Fiken does not auto-close P&L accounts annually, so a year-end `balance_check` equals cumulative unallocated result — this is expected.
- **`/bankAccounts/{id}/bankAccountStatements` does not exist**, and there is no endpoint for the raw bank-feed / superavstemming queue. Only booked data is accessible. `fiken_bank_transactions` is a client-side aggregation over `/journalEntries` filtered by the bank account's `accountCode`.
- **Server-side filters are sparse.** `/purchases` honors `paid=true|false` only. `/transactions` and `/journalEntries` ignore `dateFrom`, `startDate`, `fromDate`, and `account` — date/account filtering must happen client-side after `fetch_all=True`.
- **Amounts are in øre** (integer hundredths of NOK) throughout the API and all tool responses.
- **Contact updates use PUT, not PATCH.** The API returns 405 on PATCH. `fiken_contact_update` does read-modify-write: GET current → merge changes → PUT full object. Read-only fields (`contactId`, `createdDate`, `lastModifiedDate`, `contactPerson`, `customerAccountCode`, `supplierAccountCode`) are stripped before PUT.
- **Product updates also use PUT.** Same read-modify-write pattern. Read-only fields stripped: `productId`, `createdDate`, `lastModifiedDate`.
- **Inbox is read-only.** Only `GET /inbox` exists in the API — no create, no individual get, no upload. Fiken's OCR/invoice parsing is GUI-only.
- **OAuth token behaviour (empirical, live-tested 2026-07-28):** the token endpoint accepts **HTTP Basic** client auth (`client_id:client_secret`); the authorize endpoint rejects unregistered `redirect_uri` with a plain error page (the URI must be added verbatim in the Fiken app — `http://localhost:8473/callback`, http is allowed for `localhost`). Access tokens live **~1 hour** (`expires_in` ≈ 3600), so refresh matters. On `grant_type=refresh_token` Fiken returns a **new access token but the same refresh token** (not rotated) — `FikenClient._refresh` keeps the old refresh token when the response omits one. No `scope` param is sent (the app registration decides scope).
- **No purchase attachments** in the API. Attachments are only available on invoices (outgoing), journal entries, credit note drafts, sales, offers, and order confirmations.

## Planned stack

- Python 3.11+, packaged with `uv` (`uv sync`, `uv run python -m fiken_mcp.server`)
- `mcp` (Anthropic Python SDK), `httpx` (async), `pydantic-settings` for `.env` config
- Tests: `pytest` + `respx` for unit tests; `pytest -m integration` for demo-account tests

## Architecture (per spec §4, §7)

Layout: `src/fiken_mcp/{server,client,config}.py` + `tools/{company,invoices,contacts,accounts,journal,bank,products,reports,inbox,attachments}.py`.

Critical design constraints:

- **Single `FikenClient` singleton** shared by all tools. It holds an `asyncio.Semaphore(1)` because Fiken allows only **1 concurrent request per user** — every HTTP call must go through the semaphore.
- **`companySlug` is auto-fetched** from `/user/` at startup and cached. Tools accept an override parameter but default to `FIKEN_COMPANY_SLUG`.
- **Auth — two modes**, resolved in `Settings.use_oauth` (`config.py`):
  - **Personal token**: `FIKEN_API_TOKEN` → static `Bearer`. Simplest; wins if set.
  - **OAuth 2.0** (authorization code): `FIKEN_CLIENT_ID` + `FIKEN_CLIENT_SECRET`, no `FIKEN_API_TOKEN`. Fiken has *no* client_credentials flow, so tokens are minted by a one-time browser consent: `uv run fiken-auth` (`auth.py`) opens the authorize URL, catches the redirect on a local server (`FIKEN_REDIRECT_URI`, default `http://localhost:8473/callback` — **must be registered identically in the Fiken app**), exchanges the code (HTTP Basic client auth), and persists `{access_token, refresh_token, expires_at}` to `FIKEN_TOKEN_FILE` (default `~/.config/fiken-mcp/tokens.json`, chmod 600). `FikenClient` refreshes both **proactively** (past `expires_at`, 60 s skew) and **reactively** (one refresh+retry on a 401). Token endpoint is `https://fiken.no/oauth/token` (host differs from the API base — absolute URL passed to the shared httpx client).
- Base URL `https://api.fiken.no/api/v2`.
- **Retry policy**: 429 → exponential backoff, max 3 attempts. 401/400/404 → return structured error objects (not raised exceptions) as the MCP tool result.
- **Pagination**: list tools accept `page`/`pageSize` (default 25, max 100) and optional `fetch_all=True`; responses include `{data, total, page, pageSize}`.
- **HTTP logging**: All requests logged at DEBUG level, errors at WARNING (`fiken_mcp.client`).
- **Multipart upload**: `client.request()` supports `files` and `data` params for attachment uploads. Attachment tools accept base64-encoded content.

## Write-operation safety (spec §6)

Every tool that mutates data (POST/PUT) **must** take `confirm: bool = False`. When `confirm=False`, return a human-readable summary of what *would* happen and do nothing. Only execute the API call when `confirm=True`. This is non-negotiable — the spec's whole write story depends on it.

## Tool naming

`fiken_{resource}_{operation}` (e.g. `fiken_invoices_list`, `fiken_invoice_create`). See spec §5 for the full inventory and implementation phases (§11: read-only first, writes last).

## Domain notes

Standard norsk kontoplan: `1920` (bank), `2020` (aksjekapital), `2270` (langsiktig gjeld), `8050/8060` (finansinntekter/-kostnader). Balance-sheet and income-statement reports are the backbone for "kva er eigenkapitalen no?"-style questions.
