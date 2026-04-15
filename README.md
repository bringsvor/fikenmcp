# Fiken MCP

MCP-server som eksponerer Fiken REST API v2 som verktøy for Claude. Sjå `fiken-mcp-spec.md` for opphavleg spec og `CLAUDE.md` for dei viktigaste avvika frå spec'en (basert på empirisk API-testing).

## Status

**24 verktøy** implementert, dekker spec §11 Fase 1 (lesing), Fase 2 (bilag/bank/transaksjonar) og Fase 3 (skriving). Purchases (innkomande faktura) er inkludert sjølv om dei ikkje er i opphavleg spec.

### Lese-verktøy (19)
- **Selskap:** `fiken_company_get`, `fiken_companies_list`
- **Faktura (utgåande):** `fiken_invoices_list`, `fiken_invoice_get`
- **Innkjøp (leverandørfaktura):** `fiken_purchases_list`, `fiken_purchase_get`
- **Kontaktar:** `fiken_contacts_list`, `fiken_contact_get`
- **Kontoplan og saldo:** `fiken_accounts_list`, `fiken_account_balances`, `fiken_account_balance_get`
- **Bank:** `fiken_bank_accounts_list`, `fiken_bank_account_get`, `fiken_bank_transactions` (rekna frå journalEntries)
- **Bilag og transaksjonar:** `fiken_journal_entries_list`, `fiken_journal_entry_get`, `fiken_transactions_list`
- **Rapportar (rekna ut):** `fiken_balance_sheet`, `fiken_income_statement`

### Skrive-verktøy (5) — alle med `confirm=True`-sikring
- `fiken_contact_create`, `fiken_contact_update`
- `fiken_invoice_create`, `fiken_invoice_send`
- `fiken_journal_entry_create`

Default `confirm=False` returnerer eit strukturert dry-run-samandrag. Berre ved `confirm=True` går kallet til Fiken. Manuelle bilag blir validert (sum av linjer må vere 0) før dei blir akseptert — både i dry-run og ved faktisk skriving.

## Arkitektur-notat

- **1 concurrent request per brukar**: Fiken sin grense respekterast via `asyncio.Semaphore(1)` i `FikenClient`. Alle verktøy deler same singleton.
- **Paginering**: Fiken sende metadata i HTTP-headers (`Fiken-Api-Page-Count` osv.), 0-indeksert. `request_paginated()` i `client.py` wrapper dette og tilbyr `fetch_all=True`.
- **Beløp er i øre** gjennom heile stacken.
- **Feilhandtering**: API-feil blir returnert som strukturert dict `{error, status_code, message, fiken_error}` — aldri som exception.
- **Klient-side filter**: Fiken sitt API ignorerer dei fleste dato-/konto-filter serverside, så verktøy som `fiken_journal_entries_list` og `fiken_transactions_list` filtrerer etter `fetch_all`. Sjå `CLAUDE.md` for detaljar.

## Køyre lokalt

```bash
uv sync
cp .env.example .env
# rediger .env med din FIKEN_API_TOKEN

# direkte via stdio
uv run python -m fiken_mcp.server

# eller via MCP Inspector
npx @modelcontextprotocol/inspector uv run python -m fiken_mcp.server
```

## Tilkobling til Claude Code

```bash
claude mcp add fiken -- uv run --directory /home/tbri/bc/fikenmcp python -m fiken_mcp.server
```

Restart Claude Code og køyr `/mcp` for å sjå dei 24 verktøya.

## Tilkobling til Claude Desktop

Claude Desktop finst per i dag ikkje for Linux, men på macOS/Windows kan du leggje til i `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fiken": {
      "command": "uv",
      "args": ["run", "--directory", "/absolutt/sti/til/fikenmcp", "python", "-m", "fiken_mcp.server"],
      "env": {
        "FIKEN_API_TOKEN": "din_token_her",
        "FIKEN_COMPANY_SLUG": "din-selskap-slug"
      }
    }
  }
}
```

## Konfigurasjon (`.env`)

| Variabel | Påkravd | Default |
|---|---|---|
| `FIKEN_API_TOKEN` | ja | — |
| `FIKEN_COMPANY_SLUG` | nei | første selskap frå `/companies/` |
| `FIKEN_BASE_URL` | nei | `https://api.fiken.no/api/v2` |
