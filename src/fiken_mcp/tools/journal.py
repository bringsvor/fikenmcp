from typing import Any

from ..client import FikenClient, DEFAULT_PAGE_SIZE


async def _slug(client: FikenClient, slug: str | None) -> str | dict[str, Any]:
    return slug or await client.get_company_slug()


def _in_range(d: str | None, frm: str | None, to: str | None) -> bool:
    if d is None:
        return frm is None and to is None
    if frm is not None and d < frm:
        return False
    if to is not None and d > to:
        return False
    return True


def _entry_touches_account(entry: dict[str, Any], account_prefix: str) -> bool:
    for ln in entry.get("lines", []):
        if str(ln.get("account", "")).startswith(account_prefix):
            return True
    return False


def _transaction_touches_account(tx: dict[str, Any], account_prefix: str) -> bool:
    for entry in tx.get("entries", []):
        if _entry_touches_account(entry, account_prefix):
            return True
    return False


async def fiken_journal_entries_list(
    client: FikenClient,
    *,
    slug: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict[str, Any]:
    """List bilag (journal entries). Dato-/konto-filter er klient-side."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    result = await client.request_paginated(
        f"/companies/{resolved}/journalEntries",
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )
    if isinstance(result, dict) and result.get("error"):
        return result

    if date_from or date_to or account:
        filtered = []
        for e in result.get("data", []):
            if not _in_range(e.get("date"), date_from, date_to):
                continue
            if account and not _entry_touches_account(e, account):
                continue
            filtered.append(e)
        result = {**result, "data": filtered, "filtered_count": len(filtered)}

    return result


async def fiken_journal_entry_get(
    client: FikenClient, journal_entry_id: int, slug: str | None = None
) -> dict[str, Any]:
    """Hent enkelt bilag."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    return await client.request(
        "GET", f"/companies/{resolved}/journalEntries/{journal_entry_id}"
    )


async def fiken_journal_entry_create(
    client: FikenClient,
    *,
    date: str,
    description: str,
    lines: list[dict[str, Any]],
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Opprett manuelt bilag. Krev confirm=True.

    `lines` er liste av {amount, account}. Sum av amount MÅ vere 0 (balansert bilag).
    Beløp i øre; positivt = debet, negativt = kredit.
    """
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    total = sum(int(ln.get("amount", 0)) for ln in lines)
    if total != 0:
        return {
            "error": True,
            "status_code": 400,
            "message": f"Bilaget er ikkje balansert — sum av amount = {total} øre (må vere 0)",
            "fiken_error": None,
        }
    if len(lines) < 2:
        return {
            "error": True,
            "status_code": 400,
            "message": "Eit bilag krev minst to linjer",
            "fiken_error": None,
        }

    payload = {"date": date, "description": description, "lines": lines}

    if not confirm:
        debit_sum = sum(int(ln["amount"]) for ln in lines if int(ln.get("amount", 0)) > 0)
        accounts = sorted({str(ln.get("account")) for ln in lines})
        return {
            "dry_run": True,
            "operation": "POST /journalEntries",
            "summary": (
                f"Vil opprette bilag: {date}  '{description}'  "
                f"{len(lines)} linjer, {debit_sum} øre ({debit_sum / 100:.2f} NOK) over {accounts}"
            ),
            "payload": payload,
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "POST", f"/companies/{resolved}/journalEntries", json=payload
    )


async def fiken_transactions_list(
    client: FikenClient,
    *,
    slug: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict[str, Any]:
    """List transaksjonar (grupperer bilag på kryss-postering). Dato-/konto-filter er klient-side.

    Dato-filter matchar om *nokon* av entries i transaksjonen ligg i perioden.
    """
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    result = await client.request_paginated(
        f"/companies/{resolved}/transactions",
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )
    if isinstance(result, dict) and result.get("error"):
        return result

    if date_from or date_to or account:
        filtered = []
        for tx in result.get("data", []):
            entry_dates = [e.get("date") for e in tx.get("entries", [])]
            if date_from or date_to:
                if not any(_in_range(d, date_from, date_to) for d in entry_dates):
                    continue
            if account and not _transaction_touches_account(tx, account):
                continue
            filtered.append(tx)
        result = {**result, "data": filtered, "filtered_count": len(filtered)}

    return result
