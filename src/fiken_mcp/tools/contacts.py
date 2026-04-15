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


def _contact_payload(
    *,
    name: str | None,
    email: str | None,
    organization_number: str | None,
    phone_number: str | None,
    address: dict[str, Any] | None,
    customer: bool | None,
    supplier: bool | None,
    language: str | None,
    currency: str | None,
    inactive: bool | None,
    notes: list[str] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if name is not None:
        payload["name"] = name
    if email is not None:
        payload["email"] = email
    if organization_number is not None:
        payload["organizationNumber"] = organization_number
    if phone_number is not None:
        payload["phoneNumber"] = phone_number
    if address is not None:
        payload["address"] = address
    if customer is not None:
        payload["customer"] = customer
    if supplier is not None:
        payload["supplier"] = supplier
    if language is not None:
        payload["language"] = language
    if currency is not None:
        payload["currency"] = currency
    if inactive is not None:
        payload["inactive"] = inactive
    if notes is not None:
        payload["notes"] = notes
    return payload


async def fiken_contact_create(
    client: FikenClient,
    *,
    name: str,
    email: str | None = None,
    organization_number: str | None = None,
    phone_number: str | None = None,
    address: dict[str, Any] | None = None,
    customer: bool | None = None,
    supplier: bool | None = None,
    language: str | None = None,
    currency: str | None = None,
    notes: list[str] | None = None,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Opprett ny kontakt (kunde/leverandør). Krev confirm=True for å utføre."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    payload = _contact_payload(
        name=name,
        email=email,
        organization_number=organization_number,
        phone_number=phone_number,
        address=address,
        customer=customer,
        supplier=supplier,
        language=language,
        currency=currency,
        inactive=None,
        notes=notes,
    )

    if not confirm:
        roles = []
        if customer:
            roles.append("kunde")
        if supplier:
            roles.append("leverandør")
        roles_txt = "/".join(roles) if roles else "(ingen rolle sett)"
        return {
            "dry_run": True,
            "operation": "POST /contacts",
            "summary": f"Vil opprette kontakt '{name}' som {roles_txt}",
            "payload": payload,
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    result = await client.request(
        "POST", f"/companies/{resolved}/contacts", json=payload
    )
    return result


async def fiken_contact_update(
    client: FikenClient,
    contact_id: int,
    *,
    name: str | None = None,
    email: str | None = None,
    organization_number: str | None = None,
    phone_number: str | None = None,
    address: dict[str, Any] | None = None,
    customer: bool | None = None,
    supplier: bool | None = None,
    language: str | None = None,
    currency: str | None = None,
    inactive: bool | None = None,
    notes: list[str] | None = None,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Oppdater kontakt. Berre felt som er sette blir endra. Krev confirm=True."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    payload = _contact_payload(
        name=name,
        email=email,
        organization_number=organization_number,
        phone_number=phone_number,
        address=address,
        customer=customer,
        supplier=supplier,
        language=language,
        currency=currency,
        inactive=inactive,
        notes=notes,
    )

    if not payload:
        return {
            "error": True,
            "status_code": 400,
            "message": "Ingen felt å oppdatere",
            "fiken_error": None,
        }

    if not confirm:
        return {
            "dry_run": True,
            "operation": f"PATCH /contacts/{contact_id}",
            "summary": f"Vil oppdatere kontakt {contact_id}: {', '.join(payload.keys())}",
            "payload": payload,
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "PATCH", f"/companies/{resolved}/contacts/{contact_id}", json=payload
    )
