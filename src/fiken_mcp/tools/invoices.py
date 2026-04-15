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
