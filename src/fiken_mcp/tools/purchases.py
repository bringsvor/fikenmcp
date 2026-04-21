from typing import Any

from ..client import FikenClient, DEFAULT_PAGE_SIZE


async def _slug(client: FikenClient, slug: str | None) -> str | dict[str, Any]:
    return slug or await client.get_company_slug()


def _purchase_total(p: dict[str, Any]) -> int:
    return sum(int(ln.get("netPrice", 0)) + int(ln.get("vat", 0)) for ln in p.get("lines", []))


def _in_range(d: str | None, frm: str | None, to: str | None) -> bool:
    if d is None:
        return frm is None and to is None
    if frm is not None and d < frm:
        return False
    if to is not None and d > to:
        return False
    return True


async def fiken_purchases_list(
    client: FikenClient,
    *,
    slug: str | None = None,
    paid: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    supplier_id: int | None = None,
    kind: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict[str, Any]:
    """List innkomande (leverandør-)faktura.

    `paid` er serverside-filter. Dato-/leverandør-/kind-filter er klient-side
    (Fiken ignorerer desse query-parametrane). Set `fetch_all=True` for å få
    klient-filter på heile datasettet.
    """
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    params: dict[str, Any] = {}
    if paid is not None:
        params["paid"] = "true" if paid else "false"

    result = await client.request_paginated(
        f"/companies/{resolved}/purchases",
        params=params,
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )
    if isinstance(result, dict) and result.get("error"):
        return result

    data = result.get("data", [])
    if date_from or date_to or supplier_id is not None or kind is not None:
        filtered = []
        for p in data:
            if not _in_range(p.get("date"), date_from, date_to):
                continue
            if supplier_id is not None and p.get("supplier", {}).get("contactId") != supplier_id:
                continue
            if kind is not None and p.get("kind") != kind:
                continue
            filtered.append(p)
        result = {**result, "data": filtered, "filtered_count": len(filtered)}

    # Berik kvar post med "total" i øre for enklare bruk
    for p in result.get("data", []):
        p["total"] = _purchase_total(p)

    return result


async def fiken_purchase_get(
    client: FikenClient, purchase_id: int, slug: str | None = None
) -> dict[str, Any]:
    """Hent enkelt innkomande faktura."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    res = await client.request("GET", f"/companies/{resolved}/purchases/{purchase_id}")
    if isinstance(res, dict) and not res.get("error"):
        res["total"] = _purchase_total(res)
    return res


async def fiken_purchase_create(
    client: FikenClient,
    *,
    date: str,
    kind: str,
    lines: list[dict[str, Any]],
    currency: str = "NOK",
    supplier_id: int | None = None,
    due_date: str | None = None,
    payment_account: str | None = None,
    payment_date: str | None = None,
    kid: str | None = None,
    identifier: str | None = None,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Opprett innkomande faktura / kjøp. Krev confirm=True.

    `kind`: 'supplier' | 'cash_purchase' | 'personal' | 'personal_cash_purchase'.
    `lines`: liste av {netPrice, vat, vatType, account?, description?}. Beløp i øre.
    """
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    payload: dict[str, Any] = {
        "date": date,
        "kind": kind,
        "lines": lines,
        "currency": currency,
    }
    if supplier_id is not None:
        payload["supplierId"] = supplier_id
    if due_date is not None:
        payload["dueDate"] = due_date
    if payment_account is not None:
        payload["paymentAccount"] = payment_account
    if payment_date is not None:
        payload["paymentDate"] = payment_date
    if kid is not None:
        payload["kid"] = kid
    if identifier is not None:
        payload["identifier"] = identifier

    gross_total = sum(
        int(ln.get("netPrice", 0)) + int(ln.get("vat", 0)) for ln in lines
    )

    if not confirm:
        supplier_txt = f"leverandør {supplier_id}" if supplier_id else "ukjent leverandør"
        return {
            "dry_run": True,
            "operation": "POST /purchases",
            "summary": (
                f"Vil opprette {kind} frå {supplier_txt}, "
                f"{len(lines)} linjer, {gross_total} øre ({gross_total / 100:.2f} NOK), "
                f"dato {date}"
            ),
            "payload": payload,
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "POST", f"/companies/{resolved}/purchases", json=payload
    )
