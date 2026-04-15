# Fiken MCP Server — Spesifikasjon

> Skreddarsydd Python-basert MCP-server for Fiken, tilpassa Bringsvor Consulting AS.  
> Mål: la Claude fungere som ein intelligent rekneskapsassistent direkte mot Fiken sitt REST API v2.

---

## 1. Overordna mål

- Eksponere relevante Fiken API v2-endepunkt som MCP-verktøy
- Støtte både **lesing** (GET) og **skriving** (POST/PATCH) med tydeleg skilje
- Handsame Fiken sin begrensning på **1 concurrent request per brukar** via ein seriell køordning
- Vere trygg som standard: destruktive operasjonar krev eksplisitt `confirm=True`-parameter
- Vere enkel å køyre lokalt og koble til Claude Desktop / Claude Code

---

## 2. Teknisk stack

| Komponent | Val | Grunn |
|---|---|---|
| Språk | Python 3.11+ | Kjennskap, god MCP-støtte |
| MCP-rammeverk | `mcp` (Anthropic sitt offisielle Python SDK) | Standardisert, aktivt vedlikehalde |
| HTTP-klient | `httpx` (async) | Naturleg fit med async MCP-server |
| Konfigurasjon | `pydantic-settings` + `.env`-fil | Type-safe, enkel å overstyre |
| Pakkehandtering | `uv` | Moderne, rask |
| Køordning | `asyncio.Queue` med semaphore (maks 1) | Respekterer Fiken sin 1-request-regel |

---

## 3. Autentisering

Fiken API v2 brukar **Bearer token** (personleg API-nøkkel frå Fiken-innstillingane).

```
Authorization: Bearer <FIKEN_API_TOKEN>
```

Konfigurert via miljøvariabel:

```env
FIKEN_API_TOKEN=din_token_her
FIKEN_COMPANY_SLUG=bringsvor-consulting-as   # henta automatisk om ikkje sett
FIKEN_BASE_URL=https://api.fiken.no/api/v2  # standardverdi
```

`companySlug` skal hentast automatisk frå `/user/` ved oppstart og cachast. Serveren skal støtte fleire selskap (parameter på kvart verktøy), men defaulte til `FIKEN_COMPANY_SLUG`.

---

## 4. Prosjektstruktur

```
fiken-mcp/
├── pyproject.toml
├── .env.example
├── README.md
└── src/
    └── fiken_mcp/
        ├── __init__.py
        ├── server.py          # MCP-server, registrerer alle tools
        ├── client.py          # Fiken API-klient med seriell køordning
        ├── config.py          # Pydantic settings
        └── tools/
            ├── __init__.py
            ├── company.py     # Selskapsinfo og brukar
            ├── invoices.py    # Faktura (les + skriv)
            ├── contacts.py    # Kundar og leverandørar
            ├── accounts.py    # Kontoplan og saldo
            ├── journal.py     # Bilag og posteringar
            ├── bank.py        # Bankkontoar og bankavstemming
            ├── products.py    # Produkt/tenester
            └── reports.py     # Balanse, resultat, skattemeldingshjelp
```

---

## 5. MCP-verktøy

Alle verktøy følger namngivingskonvensjonen `fiken_{ressurs}_{operasjon}`, t.d. `fiken_invoices_list`.

### 5.1 Selskap og brukar

| Verktøy | Metode | Endepunkt | Skildring |
|---|---|---|---|
| `fiken_company_get` | GET | `/user/` + `/companies/{slug}` | Hent innlogga brukar og selskapsinfo |
| `fiken_companies_list` | GET | `/companies/` | List alle selskap brukaren har tilgang til |

### 5.2 Faktura

| Verktøy | Metode | Endepunkt | Skildring |
|---|---|---|---|
| `fiken_invoices_list` | GET | `/companies/{slug}/invoices/` | List faktura; filter på `status`, `customerId`, dato-intervall |
| `fiken_invoice_get` | GET | `/companies/{slug}/invoices/{id}` | Hent enkelt faktura med alle linjer |
| `fiken_invoice_create` | POST | `/companies/{slug}/invoices/` | Opprett ny faktura (krev `confirm=True`) |
| `fiken_invoice_send` | PATCH | `/companies/{slug}/invoices/{id}/send` | Send faktura på e-post (krev `confirm=True`) |

**Viktig for `fiken_invoices_list`:** støtte filter-parametrar:
- `status`: `DRAFT`, `SENT`, `PAID`, `OVERDUE`, `CANCELLED`
- `lastModified` dato-intervall
- `customerId`
- `issueDate` dato-intervall

### 5.3 Kontaktar

| Verktøy | Metode | Endepunkt | Skildring |
|---|---|---|---|
| `fiken_contacts_list` | GET | `/companies/{slug}/contacts/` | List kontaktar; filter på `name`, `supplierNumber`, `customerNumber` |
| `fiken_contact_get` | GET | `/companies/{slug}/contacts/{id}` | Hent enkelt kontakt |
| `fiken_contact_create` | POST | `/companies/{slug}/contacts/` | Opprett ny kontakt (krev `confirm=True`) |
| `fiken_contact_update` | PATCH | `/companies/{slug}/contacts/{id}` | Oppdater kontakt (krev `confirm=True`) |

### 5.4 Kontoplan og saldo

| Verktøy | Metode | Endepunkt | Skildring |
|---|---|---|---|
| `fiken_accounts_list` | GET | `/companies/{slug}/accounts/` | Full kontoplan med kontonummer og namn |
| `fiken_account_balances` | GET | `/companies/{slug}/accountBalances/` | Saldo per konto per dato |
| `fiken_account_balance_get` | GET | `/companies/{slug}/accountBalances/{accountCode}` | Saldo for éin konto (t.d. `2270` for marginlån) |

> **Bringsvor-spesifikt:** Dette er særleg viktig for å kunne spørje om saldo på kontoar som `2270` (marginlån), `2020` (aksjekapital/overkurs), `1920` (bank), og investeringskontoar.

### 5.5 Bilag og posteringar

| Verktøy | Metode | Endepunkt | Skildring |
|---|---|---|---|
| `fiken_journal_entries_list` | GET | `/companies/{slug}/journalEntries/` | List bilag; filter på dato, type, konto |
| `fiken_journal_entry_get` | GET | `/companies/{slug}/journalEntries/{id}` | Hent enkelt bilag med alle linjer |
| `fiken_journal_entry_create` | POST | `/companies/{slug}/journalEntries/` | Opprett manuelt bilag (krev `confirm=True`) |
| `fiken_transactions_list` | GET | `/companies/{slug}/transactions/` | List transaksjoner på konto |

> **Bringsvor-spesifikt:** Fritaksmetoden-posteringar (gevinst/tap på aksjar, konto 8050/8060), utbytte frå dotterselskap, og akkumulerte verdiar for fond (FO Real Estate, FO Private Equity) er sentrale brukstilfelle.

### 5.6 Bankkontoar

| Verktøy | Metode | Endepunkt | Skildring |
|---|---|---|---|
| `fiken_bank_accounts_list` | GET | `/companies/{slug}/bankAccounts/` | List alle bankkontoar med saldo |
| `fiken_bank_account_get` | GET | `/companies/{slug}/bankAccounts/{id}` | Hent enkelt bankkonto |
| `fiken_bank_statements_list` | GET | `/companies/{slug}/bankAccounts/{id}/bankAccountStatements/` | Hent kontoutskrift-innslag |

### 5.7 Produkt og tenester

| Verktøy | Metode | Endepunkt | Skildring |
|---|---|---|---|
| `fiken_products_list` | GET | `/companies/{slug}/products/` | List produkt/tenester |
| `fiken_product_get` | GET | `/companies/{slug}/products/{id}` | Hent enkelt produkt |

### 5.8 Rapportar

| Verktøy | Metode | Endepunkt | Skildring |
|---|---|---|---|
| `fiken_balance_sheet` | GET | `/companies/{slug}/balanceSheet/` | Balanserapport per dato |
| `fiken_income_statement` | GET | `/companies/{slug}/incomeStatements/` | Resultatrapport for periode |

> **Bringsvor-spesifikt:** Desse to rapportane er grunnlag for å svare på spørsmål som «kva er eigenkapitalen no?» og «kva er årsresultatet hittil?»

---

## 6. Tryggleik og konfirmasjon

Alle verktøy som **endrar data** (POST, PATCH, DELETE) skal:

1. Ha ein `confirm: bool = False` parameter
2. Returnere ein oppsummering av kva som *vil* skje dersom `confirm=False`
3. Faktisk utføre operasjonen berre når `confirm=True`

Eksempel (pseudokode):
```python
async def fiken_invoice_create(data: InvoiceCreate, confirm: bool = False):
    if not confirm:
        return f"Vil opprette faktura til {data.customer_name} på {data.total} kr. Kall på nytt med confirm=True for å gjennomføre."
    # ... faktisk API-kall
```

---

## 7. Seriell køordning (rate limiting)

Fiken tillèt **berre 1 concurrent request per brukar**. Implementer med `asyncio.Semaphore(1)`:

```python
class FikenClient:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(1)
    
    async def request(self, method, path, **kwargs):
        async with self._semaphore:
            # utfør HTTP-kall
            ...
```

Alle verktøy brukar same `FikenClient`-instans (singleton).

---

## 8. Feilhandtering

Serveren skal returnere strukturerte feilmeldingar som MCP-verktøyresultat (ikkje kaste exceptions):

```json
{
  "error": true,
  "status_code": 404,
  "message": "Faktura med id 12345 vart ikkje funnen",
  "fiken_error": "..."
}
```

Spesielle tilfelle:
- `401 Unauthorized` → tydeleg melding om ugyldig API-token
- `429 Too Many Requests` → automatisk retry med eksponentiell backoff (maks 3 forsøk)
- `400 Bad Request` → returnere Fiken sin valideringsmelding direkte

---

## 9. Paginering

Fiken API er paginert. Verktøy som returnerer lister skal:
- Støtte `page` og `pageSize` parametrar (default `pageSize=25`, maks `100`)
- Returnere metadata: `{ "data": [...], "total": N, "page": 1, "pageSize": 25 }`
- Automatisk hente alle sider når `fetch_all=True` (forsiktig med store datasett)

---

## 10. Oppsett og installasjon

```bash
# Installer uv om ikkje installert
curl -LsSf https://astral.sh/uv/install.sh | sh

# Klon og installer
git clone <repo>
cd fiken-mcp
uv sync

# Konfigurer
cp .env.example .env
# Rediger .env med din Fiken API-token

# Test
uv run python -m fiken_mcp.server --test
```

### Claude Desktop-konfigurasjon (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "fiken": {
      "command": "uv",
      "args": ["run", "--directory", "/absolutt/sti/til/fiken-mcp", "python", "-m", "fiken_mcp.server"],
      "env": {
        "FIKEN_API_TOKEN": "din_token_her",
        "FIKEN_COMPANY_SLUG": "bringsvor-consulting-as"
      }
    }
  }
}
```

---

## 11. Prioritert implementasjonsrekkefølge

Implementer i denne rekkefølga (MVP først):

**Fase 1 — Les-berre (trygt å køyre mot produksjon)**
1. `client.py` med auth, køordning og feilhandtering
2. `fiken_company_get`, `fiken_companies_list`
3. `fiken_invoices_list`, `fiken_invoice_get`
4. `fiken_contacts_list`, `fiken_contact_get`
5. `fiken_account_balances`, `fiken_account_balance_get`
6. `fiken_balance_sheet`, `fiken_income_statement`

**Fase 2 — Avansert lesing**
7. `fiken_journal_entries_list`, `fiken_journal_entry_get`
8. `fiken_bank_accounts_list`, `fiken_bank_statements_list`
9. `fiken_transactions_list`

**Fase 3 — Skriving (med confirm-sikring)**
10. `fiken_contact_create`, `fiken_contact_update`
11. `fiken_invoice_create`, `fiken_invoice_send`
12. `fiken_journal_entry_create`

---

## 12. Testing

- Bruk Fiken sin **demo-konto** for alle skrivetester
- Unit-testar med `pytest` + `respx` (mock av httpx)
- Integrasjonstestane mot demo-konto køyrast separat med `pytest -m integration`

---

## 13. Framtidige utvidingar (utanfor scope no)

- OAuth2-støtte (for eventuell multi-tenant Kulturspor-integrasjon)
- Automatisk avstemming av banktransaksjonar mot bilag
- Eksport av data for skattemeldingskontroll (fritaksmetoden-aggregering)
- Webhook-støtte for å trigge automatsjonar ved nye bilag

---

*Generert: April 2026 | Bringsvor Consulting AS / Torvald*
