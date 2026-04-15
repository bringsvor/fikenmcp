from mcp.server.fastmcp import FastMCP

from .client import FikenClient, DEFAULT_PAGE_SIZE
from .tools import accounts as _accounts
from .tools import bank as _bank
from .tools import contacts as _contacts
from .tools import company as _company
from .tools import invoices as _invoices
from .tools import journal as _journal
from .tools import purchases as _purchases
from .tools import reports as _reports

mcp = FastMCP("fiken")
_client: FikenClient | None = None


def _get_client() -> FikenClient:
    global _client
    if _client is None:
        _client = FikenClient()
    return _client


# ── Selskap ──────────────────────────────────────────────────────────────────
@mcp.tool()
async def fiken_company_get_tool(slug: str | None = None) -> dict:
    """Hent innlogga brukar og selskapsinfo frå Fiken."""
    return await _company.fiken_company_get(_get_client(), slug=slug)


@mcp.tool()
async def fiken_companies_list_tool(
    page: int = 0, page_size: int = DEFAULT_PAGE_SIZE, fetch_all: bool = False
) -> dict:
    """List alle selskap brukaren har tilgang til."""
    return await _company.fiken_companies_list(
        _get_client(), page=page, page_size=page_size, fetch_all=fetch_all
    )


# ── Faktura ──────────────────────────────────────────────────────────────────
@mcp.tool()
async def fiken_invoices_list_tool(
    slug: str | None = None,
    status: str | None = None,
    customer_id: int | None = None,
    issue_date_from: str | None = None,
    issue_date_to: str | None = None,
    last_modified_from: str | None = None,
    last_modified_to: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict:
    """List faktura. status: DRAFT|SENT|PAID|OVERDUE|CANCELLED. Datoar i yyyy-MM-dd."""
    return await _invoices.fiken_invoices_list(
        _get_client(),
        slug=slug,
        status=status,
        customer_id=customer_id,
        issue_date_from=issue_date_from,
        issue_date_to=issue_date_to,
        last_modified_from=last_modified_from,
        last_modified_to=last_modified_to,
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )


@mcp.tool()
async def fiken_invoice_get_tool(invoice_id: int, slug: str | None = None) -> dict:
    """Hent enkelt faktura med alle linjer."""
    return await _invoices.fiken_invoice_get(_get_client(), invoice_id=invoice_id, slug=slug)


# ── Kontaktar ────────────────────────────────────────────────────────────────
@mcp.tool()
async def fiken_contacts_list_tool(
    slug: str | None = None,
    name: str | None = None,
    customer_number: int | None = None,
    supplier_number: int | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict:
    """List kontaktar (kundar/leverandørar) med filter."""
    return await _contacts.fiken_contacts_list(
        _get_client(),
        slug=slug,
        name=name,
        customer_number=customer_number,
        supplier_number=supplier_number,
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )


@mcp.tool()
async def fiken_contact_get_tool(contact_id: int, slug: str | None = None) -> dict:
    """Hent enkelt kontakt."""
    return await _contacts.fiken_contact_get(_get_client(), contact_id=contact_id, slug=slug)


# ── Kontoplan og saldo ───────────────────────────────────────────────────────
@mcp.tool()
async def fiken_accounts_list_tool(
    slug: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict:
    """Full kontoplan — kontonummer og namn."""
    return await _accounts.fiken_accounts_list(
        _get_client(), slug=slug, page=page, page_size=page_size, fetch_all=fetch_all
    )


@mcp.tool()
async def fiken_account_balances_tool(
    date: str,
    slug: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = True,
) -> dict:
    """Saldo per konto på gitt dato (yyyy-MM-dd). Beløp i øre."""
    return await _accounts.fiken_account_balances(
        _get_client(), date=date, slug=slug, page=page, page_size=page_size, fetch_all=fetch_all
    )


@mcp.tool()
async def fiken_account_balance_get_tool(
    account_code: str, date: str, slug: str | None = None
) -> dict:
    """Saldo for éin konto på gitt dato (t.d. '2270' for marginlån). Beløp i øre."""
    return await _accounts.fiken_account_balance_get(
        _get_client(), account_code=account_code, date=date, slug=slug
    )


# ── Rapportar (rekna ut frå accountBalances) ────────────────────────────────
@mcp.tool()
async def fiken_balance_sheet_tool(date: str, slug: str | None = None) -> dict:
    """Balanse per dato (yyyy-MM-dd). Aggregert 1xxx=eigedelar, 2xxx=eigenkapital+gjeld. Beløp i øre."""
    return await _reports.fiken_balance_sheet(_get_client(), date=date, slug=slug)


@mcp.tool()
async def fiken_income_statement_tool(
    date_from: str, date_to: str, slug: str | None = None
) -> dict:
    """Resultat for periode [date_from, date_to] (yyyy-MM-dd). Beløp i øre. Positivt net_result = overskot."""
    return await _reports.fiken_income_statement(
        _get_client(), date_from=date_from, date_to=date_to, slug=slug
    )


# ── Innkomande faktura (purchases) ───────────────────────────────────────────
@mcp.tool()
async def fiken_purchases_list_tool(
    slug: str | None = None,
    paid: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    supplier_id: int | None = None,
    kind: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict:
    """List innkomande (leverandør-)faktura. `paid` er serverside; andre filter er klient-side — set fetch_all=True for å få dei anvendt på alt."""
    return await _purchases.fiken_purchases_list(
        _get_client(),
        slug=slug,
        paid=paid,
        date_from=date_from,
        date_to=date_to,
        supplier_id=supplier_id,
        kind=kind,
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )


@mcp.tool()
async def fiken_purchase_get_tool(purchase_id: int, slug: str | None = None) -> dict:
    """Hent enkelt innkomande faktura."""
    return await _purchases.fiken_purchase_get(
        _get_client(), purchase_id=purchase_id, slug=slug
    )


# ── Bankkontoar ─────────────────────────────────────────────────────────────
@mcp.tool()
async def fiken_bank_accounts_list_tool(
    slug: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict:
    """List alle bankkontoar (med reconciledBalance / reconciledDate)."""
    return await _bank.fiken_bank_accounts_list(
        _get_client(), slug=slug, page=page, page_size=page_size, fetch_all=fetch_all
    )


@mcp.tool()
async def fiken_bank_account_get_tool(bank_account_id: int, slug: str | None = None) -> dict:
    """Hent enkelt bankkonto."""
    return await _bank.fiken_bank_account_get(
        _get_client(), bank_account_id=bank_account_id, slug=slug
    )


@mcp.tool()
async def fiken_bank_transactions_tool(
    bank_account_id: int,
    date_from: str,
    date_to: str,
    slug: str | None = None,
) -> dict:
    """Bokførde bank-transaksjonar for éin bankkonto i ein periode. Beløp i øre.

    OBS: Fiken API eksponerer ikkje den råe bank-feed-køen (superavstemming);
    dette er berre bokførte postar, aggregert frå journalEntries.
    """
    return await _bank.fiken_bank_transactions(
        _get_client(),
        bank_account_id=bank_account_id,
        date_from=date_from,
        date_to=date_to,
        slug=slug,
    )


# ── Bilag og transaksjonar ──────────────────────────────────────────────────
@mcp.tool()
async def fiken_journal_entries_list_tool(
    slug: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict:
    """List bilag. Dato-/konto-filter er klient-side; set fetch_all=True for full dekning. `account` matchar prefix på kontokode (t.d. '1920' eller '1920:10001')."""
    return await _journal.fiken_journal_entries_list(
        _get_client(),
        slug=slug,
        date_from=date_from,
        date_to=date_to,
        account=account,
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )


@mcp.tool()
async def fiken_journal_entry_get_tool(
    journal_entry_id: int, slug: str | None = None
) -> dict:
    """Hent enkelt bilag."""
    return await _journal.fiken_journal_entry_get(
        _get_client(), journal_entry_id=journal_entry_id, slug=slug
    )


@mcp.tool()
async def fiken_transactions_list_tool(
    slug: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict:
    """List transaksjonar (grupperte bilag). Dato-/konto-filter er klient-side."""
    return await _journal.fiken_transactions_list(
        _get_client(),
        slug=slug,
        date_from=date_from,
        date_to=date_to,
        account=account,
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
