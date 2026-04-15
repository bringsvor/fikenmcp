from typing import Any

from ..client import FikenClient, DEFAULT_PAGE_SIZE


async def _slug(client: FikenClient, slug: str | None) -> str | dict[str, Any]:
    return slug or await client.get_company_slug()


async def fiken_contacts_list(
    client: FikenClient,
    *,
    slug: str | None = None,
    name: str | None = None,
    customer_number: int | None = None,
    supplier_number: int | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict[str, Any]:
    """List kontaktar (kundar/leverandørar) med filter og paginering."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    params: dict[str, Any] = {}
    if name is not None:
        params["name"] = name
    if customer_number is not None:
        params["customerNumber"] = customer_number
    if supplier_number is not None:
        params["supplierNumber"] = supplier_number

    return await client.request_paginated(
        f"/companies/{resolved}/contacts/",
        params=params,
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )


async def fiken_contact_get(
    client: FikenClient, contact_id: int, slug: str | None = None
) -> dict[str, Any]:
    """Hent enkelt kontakt."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    return await client.request("GET", f"/companies/{resolved}/contacts/{contact_id}")
