from typing import Any

from ..client import FikenClient, DEFAULT_PAGE_SIZE


async def _slug(client: FikenClient, slug: str | None) -> str | dict[str, Any]:
    return slug or await client.get_company_slug()


def _product_payload(
    *,
    name: str | None,
    product_number: str | None,
    unit_price: int | None,
    vat_type: str | None,
    income_account: str | None,
    active: bool | None,
    stock: bool | None,
    note: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if name is not None:
        payload["name"] = name
    if product_number is not None:
        payload["productNumber"] = product_number
    if unit_price is not None:
        payload["unitPrice"] = unit_price
    if vat_type is not None:
        payload["vatType"] = vat_type
    if income_account is not None:
        payload["incomeAccount"] = income_account
    if active is not None:
        payload["active"] = active
    if stock is not None:
        payload["stock"] = stock
    if note is not None:
        payload["note"] = note
    return payload


async def fiken_products_list(
    client: FikenClient,
    *,
    slug: str | None = None,
    name: str | None = None,
    product_number: str | None = None,
    active: bool | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict[str, Any]:
    """List produkt/tenester med filter og paginering."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    params: dict[str, Any] = {}
    if name is not None:
        params["name"] = name
    if product_number is not None:
        params["productNumber"] = product_number
    if active is not None:
        params["active"] = "true" if active else "false"

    return await client.request_paginated(
        f"/companies/{resolved}/products/",
        params=params,
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )


async def fiken_product_get(
    client: FikenClient, product_id: int, slug: str | None = None
) -> dict[str, Any]:
    """Hent enkelt produkt."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    return await client.request("GET", f"/companies/{resolved}/products/{product_id}")


async def fiken_product_create(
    client: FikenClient,
    *,
    name: str,
    unit_price: int | None = None,
    vat_type: str | None = None,
    income_account: str | None = None,
    product_number: str | None = None,
    active: bool | None = None,
    stock: bool | None = None,
    note: str | None = None,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Opprett nytt produkt. Krev confirm=True for å utføre."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    payload = _product_payload(
        name=name,
        product_number=product_number,
        unit_price=unit_price,
        vat_type=vat_type,
        income_account=income_account,
        active=active,
        stock=stock,
        note=note,
    )

    if not confirm:
        price_txt = f"{unit_price} øre ({unit_price / 100:.2f} NOK)" if unit_price else "ikkje sett"
        return {
            "dry_run": True,
            "operation": "POST /products",
            "summary": f"Vil opprette produkt '{name}', pris {price_txt}",
            "payload": payload,
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "POST", f"/companies/{resolved}/products", json=payload
    )


async def fiken_product_update(
    client: FikenClient,
    product_id: int,
    *,
    name: str | None = None,
    unit_price: int | None = None,
    vat_type: str | None = None,
    income_account: str | None = None,
    product_number: str | None = None,
    active: bool | None = None,
    stock: bool | None = None,
    note: str | None = None,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Oppdater produkt. Berre felt som er sette blir endra. Krev confirm=True."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    payload = _product_payload(
        name=name,
        product_number=product_number,
        unit_price=unit_price,
        vat_type=vat_type,
        income_account=income_account,
        active=active,
        stock=stock,
        note=note,
    )

    if not payload:
        return {
            "error": True,
            "status_code": 400,
            "message": "Ingen felt å oppdatere",
            "fiken_error": None,
        }

    # Read-modify-write: Fiken krev PUT med fullt objekt
    current = await client.request(
        "GET", f"/companies/{resolved}/products/{product_id}"
    )
    if isinstance(current, dict) and current.get("error"):
        return current

    full_payload = dict(current)
    full_payload.update(payload)
    for key in ("productId", "createdDate", "lastModifiedDate"):
        full_payload.pop(key, None)

    if not confirm:
        return {
            "dry_run": True,
            "operation": f"PUT /products/{product_id}",
            "summary": f"Vil oppdatere produkt {product_id}: {', '.join(payload.keys())}",
            "payload": payload,
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "PUT", f"/companies/{resolved}/products/{product_id}", json=full_payload
    )
