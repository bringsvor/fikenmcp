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
