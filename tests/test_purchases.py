import httpx

from fiken_mcp.tools.purchases import fiken_purchases_list, fiken_purchase_get, fiken_purchase_create

SLUG = "test-company"

PURCHASE = {
    "purchaseId": 1,
    "date": "2026-03-15",
    "kind": "invoice",
    "supplier": {"contactId": 42},
    "lines": [{"netPrice": 10000, "vat": 2500}],
}


def _list_response(data):
    return httpx.Response(
        200,
        json=data,
        headers={"fiken-api-result-count": str(len(data)), "fiken-api-page-count": "1"},
    )


async def test_purchases_list(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/purchases").mock(
        return_value=_list_response([PURCHASE])
    )
    result = await fiken_purchases_list(client, slug=SLUG)
    assert len(result["data"]) == 1
    assert result["data"][0]["total"] == 12500


async def test_purchases_list_client_side_date_filter(client, mock_api):
    purchases = [
        {**PURCHASE, "purchaseId": 1, "date": "2026-02-01"},
        {**PURCHASE, "purchaseId": 2, "date": "2026-03-15"},
    ]
    mock_api.get(f"/companies/{SLUG}/purchases").mock(
        return_value=_list_response(purchases)
    )
    result = await fiken_purchases_list(
        client, slug=SLUG, date_from="2026-03-01", date_to="2026-03-31", fetch_all=True
    )
    assert len(result["data"]) == 1
    assert result["data"][0]["purchaseId"] == 2


async def test_purchases_list_supplier_filter(client, mock_api):
    purchases = [
        {**PURCHASE, "purchaseId": 1, "supplier": {"contactId": 42}},
        {**PURCHASE, "purchaseId": 2, "supplier": {"contactId": 99}},
    ]
    mock_api.get(f"/companies/{SLUG}/purchases").mock(
        return_value=_list_response(purchases)
    )
    result = await fiken_purchases_list(
        client, slug=SLUG, supplier_id=42, fetch_all=True
    )
    assert len(result["data"]) == 1
    assert result["data"][0]["purchaseId"] == 1


async def test_purchase_get(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/purchases/1").respond(200, json=PURCHASE)
    result = await fiken_purchase_get(client, 1, slug=SLUG)
    assert result["purchaseId"] == 1
    assert result["total"] == 12500


# --- Create ---


async def test_purchase_create_dry_run(client, mock_api):
    lines = [{"netPrice": 80000, "vat": 20000, "vatType": "HIGH", "account": "4000"}]
    result = await fiken_purchase_create(
        client, date="2026-04-16", kind="invoice", lines=lines,
        supplier_id=42, slug=SLUG,
    )
    assert result["dry_run"] is True
    assert "invoice" in result["summary"]
    assert "leverandør 42" in result["summary"]
    assert "100000 øre" in result["summary"]
    assert result["payload"]["currency"] == "NOK"


async def test_purchase_create_confirm(client, mock_api):
    mock_api.post(f"/companies/{SLUG}/purchases").respond(
        201, json={}, headers={"Location": "/purchases/5"}
    )
    lines = [{"netPrice": 50000, "vat": 12500, "vatType": "HIGH"}]
    result = await fiken_purchase_create(
        client, date="2026-04-16", kind="cash_purchase", lines=lines,
        payment_account="1920", payment_date="2026-04-16",
        slug=SLUG, confirm=True,
    )
    assert result == {}


async def test_purchase_create_with_optional_fields(client, mock_api):
    lines = [{"netPrice": 10000, "vat": 0, "vatType": "NONE"}]
    result = await fiken_purchase_create(
        client, date="2026-04-16", kind="invoice", lines=lines,
        due_date="2026-05-16", kid="12345678", identifier="F-2026-042",
        slug=SLUG,
    )
    assert result["dry_run"] is True
    assert result["payload"]["dueDate"] == "2026-05-16"
    assert result["payload"]["kid"] == "12345678"
    assert result["payload"]["identifier"] == "F-2026-042"
