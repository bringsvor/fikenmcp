from typing import Any

from ..client import FikenClient, DEFAULT_PAGE_SIZE


async def _slug(client: FikenClient, slug: str | None) -> str | dict[str, Any]:
    return slug or await client.get_company_slug()


async def fiken_invoices_list(
    client: FikenClient,
    *,
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
) -> dict[str, Any]:
    """List faktura med filter og paginering."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    params: dict[str, Any] = {}
    if status is not None:
        params["invoiceStatus"] = status
    if customer_id is not None:
        params["customerId"] = customer_id
    if issue_date_from is not None:
        params["issueDateFrom"] = issue_date_from
    if issue_date_to is not None:
        params["issueDateTo"] = issue_date_to
    if last_modified_from is not None:
        params["lastModifiedFrom"] = last_modified_from
    if last_modified_to is not None:
        params["lastModifiedTo"] = last_modified_to

    return await client.request_paginated(
        f"/companies/{resolved}/invoices/",
        params=params,
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )


async def fiken_invoice_get(
    client: FikenClient, invoice_id: int, slug: str | None = None
) -> dict[str, Any]:
    """Hent enkelt faktura med alle linjer."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    return await client.request("GET", f"/companies/{resolved}/invoices/{invoice_id}")


async def fiken_invoice_create(
    client: FikenClient,
    *,
    customer_id: int,
    issue_date: str,
    due_date: str,
    lines: list[dict[str, Any]],
    bank_account_code: str,
    invoice_text: str | None = None,
    your_reference: str | None = None,
    cash: bool = False,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Opprett ny faktura. Krev confirm=True for å utføre.

    `lines` er ei liste av {description, unitPrice, quantity, vatType, incomeAccount?, productId?, discount?}.
    Beløp i øre. `unitPrice` og `quantity` er påkravd. Treng `incomeAccount` (t.d. "3000") eller `productId`.
    """
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    payload: dict[str, Any] = {
        "customerId": customer_id,
        "issueDate": issue_date,
        "dueDate": due_date,
        "lines": lines,
        "bankAccountCode": bank_account_code,
        "cash": cash,
    }
    if invoice_text is not None:
        payload["invoiceText"] = invoice_text
    if your_reference is not None:
        payload["yourReference"] = your_reference

    def _line_gross(ln: dict[str, Any]) -> int:
        if "netPrice" in ln or "vat" in ln:
            return int(ln.get("netPrice", 0)) + int(ln.get("vat", 0))
        return int(ln.get("unitPrice", 0)) * int(ln.get("quantity", 1))

    gross_total = sum(_line_gross(ln) for ln in lines)

    if not confirm:
        return {
            "dry_run": True,
            "operation": "POST /invoices",
            "summary": (
                f"Vil opprette faktura til customerId={customer_id}, "
                f"{len(lines)} linjer, brutto={gross_total} øre "
                f"({gross_total / 100:.2f} NOK), utstedt {issue_date}, forfall {due_date}"
            ),
            "payload": payload,
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "POST", f"/companies/{resolved}/invoices", json=payload
    )


async def fiken_invoice_send(
    client: FikenClient,
    invoice_id: int,
    *,
    method: str = "email",
    email_address: str | None = None,
    message: str | None = None,
    include_kid: bool = True,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Send faktura (email/letter/auto). Krev confirm=True for å utføre.

    `method`: 'email' | 'letter' | 'sms' | 'auto'.
    """
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    payload: dict[str, Any] = {"invoiceId": invoice_id, "method": method, "includeKid": include_kid}
    if email_address is not None:
        payload["emailAddress"] = email_address
    if message is not None:
        payload["message"] = message

    if not confirm:
        dest = email_address or f"(standardmottakar for faktura {invoice_id})"
        return {
            "dry_run": True,
            "operation": "POST /sendInvoice",
            "summary": f"Vil sende faktura {invoice_id} via {method} til {dest}",
            "payload": payload,
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "POST", f"/companies/{resolved}/sendInvoice", json=payload
    )
