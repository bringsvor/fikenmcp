from typing import Any

from ..client import FikenClient, DEFAULT_PAGE_SIZE
from .journal import fiken_journal_entries_list


async def _slug(client: FikenClient, slug: str | None) -> str | dict[str, Any]:
    return slug or await client.get_company_slug()


async def fiken_bank_accounts_list(
    client: FikenClient,
    *,
    slug: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict[str, Any]:
    """List alle bankkontoar med `reconciledBalance` og `reconciledDate`."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    return await client.request_paginated(
        f"/companies/{resolved}/bankAccounts",
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )


async def fiken_bank_account_get(
    client: FikenClient, bank_account_id: int, slug: str | None = None
) -> dict[str, Any]:
    """Hent enkelt bankkonto."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    return await client.request(
        "GET", f"/companies/{resolved}/bankAccounts/{bank_account_id}"
    )


async def fiken_bank_transactions(
    client: FikenClient,
    bank_account_id: int,
    date_from: str,
    date_to: str,
    *,
    slug: str | None = None,
) -> dict[str, Any]:
    """Rekneskapsførde bank-transaksjonar for éin bankkonto i ein periode.

    Merk: dette er bokført data, ikkje råe bank-feed-linjer. Fiken API
    eksponerer ikkje den råe bank-integrasjonskøen (superavstemming).

    Aggregerer alle journalEntries i perioden som har ei linje på bankkontoen
    sin accountCode (t.d. '1920:10001'), og returnerer bank-sida av kvar
    post pluss motkontoane.
    """
    account = await fiken_bank_account_get(client, bank_account_id, slug=slug)
    if isinstance(account, dict) and account.get("error"):
        return account
    account_code = account.get("accountCode")
    if not account_code:
        return {
            "error": True,
            "status_code": 500,
            "message": f"Bankkonto {bank_account_id} manglar accountCode",
            "fiken_error": account,
        }

    entries_res = await fiken_journal_entries_list(
        client,
        slug=slug,
        date_from=date_from,
        date_to=date_to,
        account=account_code,
        fetch_all=True,
    )
    if isinstance(entries_res, dict) and entries_res.get("error"):
        return entries_res

    transactions: list[dict[str, Any]] = []
    total = 0
    for e in entries_res.get("data", []):
        bank_lines = [ln for ln in e.get("lines", []) if str(ln.get("account", "")) == account_code]
        other_lines = [ln for ln in e.get("lines", []) if str(ln.get("account", "")) != account_code]
        amount = sum(int(ln.get("amount", 0)) for ln in bank_lines)
        total += amount
        transactions.append(
            {
                "date": e.get("date"),
                "journal_entry_id": e.get("journalEntryId"),
                "journal_entry_number": e.get("journalEntryNumber"),
                "description": e.get("description"),
                "amount": amount,
                "counterpart_accounts": sorted(
                    {str(ln.get("account")) for ln in other_lines if ln.get("account")}
                ),
                "counterpart_lines": other_lines,
            }
        )

    transactions.sort(key=lambda t: (t["date"] or "", t["journal_entry_number"] or 0))

    return {
        "bank_account_id": bank_account_id,
        "bank_account_name": account.get("name"),
        "bank_account_code": account_code,
        "date_from": date_from,
        "date_to": date_to,
        "currency": "NOK (øre)",
        "transaction_count": len(transactions),
        "net_amount": total,
        "reconciled_balance": account.get("reconciledBalance"),
        "reconciled_date": account.get("reconciledDate"),
        "transactions": transactions,
    }
