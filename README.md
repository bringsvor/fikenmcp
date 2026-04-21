# Fiken MCP

MCP-server som let deg snakke med Fiken-rekneskapen din via Claude. Still spørsmål om balanse, faktura, kontaktar — eller opprett bilag, faktura og kreditnota med naturleg språk.

## Kvifor?

Fiken har eit godt API, men det krev at du veit kva endepunkt du skal kalle, korleis paginering fungerer, og at beløp er i øre. Denne MCP-serveren gjer alt det for deg — du spør berre Claude.

## Status

**40 verktøy** | **105 testar** | Alle grøne

### Lese-verktøy (25)
- **Selskap:** `fiken_company_get`, `fiken_companies_list`
- **Faktura:** `fiken_invoices_list`, `fiken_invoice_get`
- **Kreditnota:** `fiken_credit_notes_list`, `fiken_credit_note_get`
- **Innkjøp:** `fiken_purchases_list`, `fiken_purchase_get`
- **Kontaktar:** `fiken_contacts_list`, `fiken_contact_get`
- **Produkt:** `fiken_products_list`, `fiken_product_get`
- **Kontoplan/saldo:** `fiken_accounts_list`, `fiken_account_balances`, `fiken_account_balance_get`
- **Bank:** `fiken_bank_accounts_list`, `fiken_bank_account_get`, `fiken_bank_transactions`
- **Bilag/transaksjonar:** `fiken_journal_entries_list`, `fiken_journal_entry_get`, `fiken_transactions_list`
- **Innboks:** `fiken_inbox_list`
- **Vedlegg:** `fiken_invoice_attachments_list`, `fiken_journal_entry_attachments_list`
- **Rapportar:** `fiken_balance_sheet`, `fiken_income_statement`

### Skrive-verktøy (14) — alle med `confirm=True`-sikring
- **Kontaktar:** `fiken_contact_create`, `fiken_contact_update`
- **Faktura:** `fiken_invoice_create`, `fiken_invoice_send`
- **Kreditnota:** `fiken_credit_note_create_full`, `fiken_credit_note_create_partial`, `fiken_credit_note_send`
- **Innkjøp:** `fiken_purchase_create`
- **Produkt:** `fiken_product_create`, `fiken_product_update`
- **Bilag:** `fiken_journal_entry_create`
- **Vedlegg:** `fiken_invoice_attachment_add`, `fiken_journal_entry_attachment_add`

Alle skriveverkty returnerer eit dry-run-samandrag som standard. Berre ved `confirm=True` går kallet til Fiken.

## Kom i gang

### Krav

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (CLI)

### 1. Klone og installer

```bash
git clone git@github.com:bringsvor/fikenmcp.git
cd fikenmcp
uv sync --extra dev
```

### 2. Lag Fiken API-token

1. Logg inn på [fiken.no](https://fiken.no)
2. Gå til **Innstillinger** (tannhjulet oppe til høgre)
3. Vel **Fiken API** i sidemenyen
4. Klikk **Opprett nytt API-token**
5. Gi tokenet eit namn (t.d. "Claude MCP") og lagre

### 3. Konfigurer

```bash
cp .env.example .env
# Rediger .env med din FIKEN_API_TOKEN
# FIKEN_COMPANY_SLUG er valfritt — auto-oppdaga frå API-et
```

### 4. Køyr testar (valfritt, men trygt)

```bash
uv run python -m pytest tests/ -v
```

### 5. Kople til Claude Code

```bash
claude mcp add fiken -- uv run --directory $(pwd) python -m fiken_mcp.server
```

Restart Claude Code og køyr `/mcp` for å sjå dei 40 verktøya.

### 6. Prøv det!

Her er nokre eksempel-spørsmål du kan stille Claude:

- "Kva er eigenkapitalen per i dag?"
- "Vis meg ubetalte innkjøpsfaktura"
- "Kva er banksaldoen?"
- "List alle kontaktar i Ålesund"
- "Vis resultatrekneskapet for Q1 2026"
- "Opprett ein faktura til Acme AS for 10 konsulenttimar à 1500 kr"

## Tilkobling til Claude Desktop

Claude Desktop (macOS/Windows) kan koplast til via `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fiken": {
      "command": "uv",
      "args": ["run", "--directory", "/sti/til/fikenmcp", "python", "-m", "fiken_mcp.server"],
      "env": {
        "FIKEN_API_TOKEN": "din_token_her"
      }
    }
  }
}
```

## Konfigurasjon (`.env`)

| Variabel | Påkravd | Default |
|---|---|---|
| `FIKEN_API_TOKEN` | ja | — |
| `FIKEN_COMPANY_SLUG` | nei | auto-oppdaga frå API-et |
| `FIKEN_BASE_URL` | nei | `https://api.fiken.no/api/v2` |

## Arkitektur

- **Semaphore(1)**: Fiken tillèt 1 samtidsforespurnad per brukar — alle kall går gjennom ein semaphore.
- **Beløp i øre** gjennom heile stacken (1 kr = 100 øre).
- **Feilhandtering**: API-feil kjem som strukturert dict, aldri som exception.
- **HTTP-logging**: DEBUG for alle requests, WARNING for feil (`fiken_mcp.client`).
- **Klient-side filter**: Fiken sitt API ignorerer mange filter serverside — vi filtrerer etter `fetch_all`. Sjå `CLAUDE.md` for detaljar.

## Støtt prosjektet

Om du har nytte av Fiken MCP, kan du støtte vidare utvikling:

- **Via Fiken** — spør Claude: *"Eg vil støtte Fiken MCP-prosjektet"* — han opprettar eit innkjøp i Fiken-en din (default 500 NOK)
- **Via Stripe** — [Betal her](https://buy.stripe.com/28EcN5bKP665aeE4bLeME02)

---

Utvikla av [Bringsvor Consulting AS](https://www.bringsvor.com). Treng du skreddarsydd utvikling med Claude, Fiken-integrasjon, eller andre AI-prosjekt? Ta kontakt via bringsvor.com.
