import json

import httpx

from fiken_mcp.tools.products import (
    fiken_products_list,
    fiken_product_get,
    fiken_product_create,
    fiken_product_update,
)

SLUG = "test-company"

PRODUCT = {
    "productId": 1,
    "createdDate": "2024-01-01",
    "lastModifiedDate": "2024-06-01",
    "name": "Konsulenttimar",
    "productNumber": "P001",
    "unitPrice": 150000,
    "vatType": "HIGH",
    "incomeAccount": "3000",
    "active": True,
    "stock": False,
    "note": "",
}


def _list_response(data):
    return httpx.Response(
        200,
        json=data,
        headers={"fiken-api-result-count": str(len(data)), "fiken-api-page-count": "1"},
    )


# --- List ---


async def test_products_list(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/products/").mock(
        return_value=_list_response([PRODUCT])
    )
    result = await fiken_products_list(client, slug=SLUG)
    assert len(result["data"]) == 1
    assert result["data"][0]["name"] == "Konsulenttimar"


async def test_products_list_with_filters(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/products/").mock(
        return_value=_list_response([PRODUCT])
    )
    result = await fiken_products_list(
        client, slug=SLUG, name="Konsulent", active=True
    )
    assert len(result["data"]) == 1


# --- Get ---


async def test_product_get(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/products/1").respond(200, json=PRODUCT)
    result = await fiken_product_get(client, 1, slug=SLUG)
    assert result["productId"] == 1
    assert result["unitPrice"] == 150000


# --- Create ---


async def test_product_create_dry_run(client, mock_api):
    result = await fiken_product_create(
        client, name="Nytt produkt", unit_price=200000, vat_type="HIGH", slug=SLUG
    )
    assert result["dry_run"] is True
    assert "POST" in result["operation"]
    assert result["payload"]["name"] == "Nytt produkt"
    assert "200000 øre" in result["summary"]


async def test_product_create_confirm(client, mock_api):
    mock_api.post(f"/companies/{SLUG}/products").respond(
        201, json={"productId": 2}
    )
    result = await fiken_product_create(
        client, name="Nytt produkt", unit_price=200000, slug=SLUG, confirm=True
    )
    assert result == {"productId": 2}


# --- Update (PUT read-modify-write) ---


async def test_product_update_dry_run(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/products/1").respond(200, json=PRODUCT)
    result = await fiken_product_update(
        client, 1, unit_price=175000, slug=SLUG
    )
    assert result["dry_run"] is True
    assert "PUT" in result["operation"]
    assert result["payload"] == {"unitPrice": 175000}


async def test_product_update_confirm_sends_put(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/products/1").respond(200, json=PRODUCT)
    put_route = mock_api.put(f"/companies/{SLUG}/products/1").respond(200, json={})

    result = await fiken_product_update(
        client, 1, unit_price=175000, slug=SLUG, confirm=True
    )
    assert result == {}
    assert put_route.calls[0].request.method == "PUT"


async def test_product_update_strips_readonly_fields(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/products/1").respond(200, json=PRODUCT)
    put_route = mock_api.put(f"/companies/{SLUG}/products/1").respond(200, json={})

    await fiken_product_update(
        client, 1, active=False, slug=SLUG, confirm=True
    )

    body = json.loads(put_route.calls[0].request.content)
    for key in ("productId", "createdDate", "lastModifiedDate"):
        assert key not in body, f"Read-only field {key} should be stripped"


async def test_product_update_merges_with_current(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/products/1").respond(200, json=PRODUCT)
    put_route = mock_api.put(f"/companies/{SLUG}/products/1").respond(200, json={})

    await fiken_product_update(
        client, 1, name="Rådgjevartimar", slug=SLUG, confirm=True
    )

    body = json.loads(put_route.calls[0].request.content)
    assert body["name"] == "Rådgjevartimar"
    assert body["unitPrice"] == 150000  # preserved from GET
    assert body["vatType"] == "HIGH"  # preserved from GET


async def test_product_update_no_fields_returns_error(client, mock_api):
    result = await fiken_product_update(client, 1, slug=SLUG)
    assert result["error"] is True
    assert result["status_code"] == 400


async def test_product_update_propagates_get_error(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/products/999").respond(
        404, json={"message": "Not found"}
    )
    result = await fiken_product_update(
        client, 999, name="X", slug=SLUG, confirm=True
    )
    assert result["error"] is True
    assert result["status_code"] == 404
