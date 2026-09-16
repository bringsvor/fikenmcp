from typing import Any

from ..client import FikenClient, DEFAULT_PAGE_SIZE


async def _slug(client: FikenClient, slug: str | None) -> str | dict[str, Any]:
    return slug or await client.get_company_slug()


async def fiken_credit_notes_list(
    client: FikenClient,
    *,
    slug: str | None = None,
    issue_date_from: str | None = None,
    issue_date_to: str | None = None,
    customer_id: int | None = None,
    settled: bool | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict[str, Any]:
    """List kreditnotaer med filter og paginering."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    params: dict[str, Any] = {}
    if issue_date_from is not None:
        params["issueDateFrom"] = issue_date_from
    if issue_date_to is not None:
        params["issueDateTo"] = issue_date_to
    if customer_id is not None:
        params["customerId"] = customer_id
    if settled is not None:
        params["settled"] = "true" if settled else "false"

    return await client.request_paginated(
        f"/companies/{resolved}/creditNotes",
        params=params,
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )


async def fiken_credit_note_get(
    client: FikenClient, credit_note_id: int, slug: str | None = None
) -> dict[str, Any]:
    """Hent enkelt kreditnota."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    return await client.request(
        "GET", f"/companies/{resolved}/creditNotes/{credit_note_id}"
    )


async def fiken_credit_note_create_full(
    client: FikenClient,
    *,
    invoice_id: int,
    issue_date: str,
    credit_note_text: str | None = None,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Full kreditering av ein faktura. Krev confirm=True."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    payload: dict[str, Any] = {
        "invoiceId": invoice_id,
        "issueDate": issue_date,
    }
    if credit_note_text is not None:
        payload["creditNoteText"] = credit_note_text

    if not confirm:
        return {
            "dry_run": True,
            "operation": "POST /creditNotes/full",
            "summary": (
                f"Vil opprette full kreditnota for faktura {invoice_id}, "
                f"utstedt {issue_date}"
            ),
            "payload": payload,
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "POST", f"/companies/{resolved}/creditNotes/full", json=payload
    )


async def fiken_credit_note_create_partial(
    client: FikenClient,
    *,
    issue_date: str,
    lines: list[dict[str, Any]],
    invoice_id: int | None = None,
    contact_id: int | None = None,
    credit_note_text: str | None = None,
    our_reference: str | None = None,
    your_reference: str | None = None,
    currency: str | None = None,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Delvis kreditering. Krev confirm=True.

    `lines`: liste av {unitPrice, quantity, vatType?, description?, incomeAccount?, productId?}.
    Beløp i øre.
    """
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    payload: dict[str, Any] = {
        "issueDate": issue_date,
        "lines": lines,
    }
    if invoice_id is not None:
        payload["invoiceId"] = invoice_id
    if contact_id is not None:
        payload["contactId"] = contact_id
    if credit_note_text is not None:
        payload["creditNoteText"] = credit_note_text
    if our_reference is not None:
        payload["ourReference"] = our_reference
    if your_reference is not None:
        payload["yourReference"] = your_reference
    if currency is not None:
        payload["currency"] = currency

    gross_total = sum(
        int(ln.get("unitPrice", 0)) * int(ln.get("quantity", 1))
        for ln in lines
    )

    ref = f"faktura {invoice_id}" if invoice_id else f"kontakt {contact_id}" if contact_id else "ukjent"

    if not confirm:
        return {
            "dry_run": True,
            "operation": "POST /creditNotes/partial",
            "summary": (
                f"Vil opprette delvis kreditnota for {ref}, "
                f"{len(lines)} linjer, {gross_total} øre ({gross_total / 100:.2f} NOK), "
                f"utstedt {issue_date}"
            ),
            "payload": payload,
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "POST", f"/companies/{resolved}/creditNotes/partial", json=payload
    )


async def fiken_credit_note_set_counter(
    client: FikenClient,
    *,
    value: int = 20001,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Initialiser kreditnota-serien med eit startnummer. Kan berre gjerast éin
    gong, før den første kreditnotaen blir oppretta. Krev confirm=True."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    payload: dict[str, Any] = {"value": value}

    if not confirm:
        return {
            "dry_run": True,
            "operation": "POST /creditNotes/counter",
            "summary": f"Vil initialisere kreditnota-telaren til å starte på {value}",
            "payload": payload,
            "note": (
                "Kall på nytt med confirm=True for å utføre. Verkar berre før "
                "den første kreditnotaen er oppretta."
            ),
        }

    return await client.request(
        "POST", f"/companies/{resolved}/creditNotes/counter", json=payload
    )


async def fiken_credit_note_send(
    client: FikenClient,
    credit_note_id: int,
    *,
    method: str = "email",
    email_address: str | None = None,
    message: str | None = None,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Send kreditnota via email/letter/auto. Krev confirm=True."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    payload: dict[str, Any] = {
        "creditNoteId": credit_note_id,
        "method": method,
    }
    if email_address is not None:
        payload["emailAddress"] = email_address
    if message is not None:
        payload["message"] = message

    if not confirm:
        dest = email_address or f"(standardmottakar for kreditnota {credit_note_id})"
        return {
            "dry_run": True,
            "operation": "POST /creditNotes/send",
            "summary": f"Vil sende kreditnota {credit_note_id} via {method} til {dest}",
            "payload": payload,
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "POST", f"/companies/{resolved}/creditNotes/send", json=payload
    )
