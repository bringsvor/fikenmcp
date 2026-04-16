import httpx
import respx
from respx.patterns import M

from fiken_mcp.client import FikenClient

BASE = "https://api.fiken.no/api/v2"


async def test_request_get(client, mock_api):
    mock_api.get("/companies/test-company/contacts/1").respond(
        200, json={"contactId": 1, "name": "Acme"}
    )
    result = await client.request("GET", "/companies/test-company/contacts/1")
    assert result == {"contactId": 1, "name": "Acme"}


async def test_request_post(client, mock_api):
    mock_api.post("/companies/test-company/contacts").respond(
        201, json={"contactId": 2}, headers={"Location": "/contacts/2"}
    )
    result = await client.request(
        "POST", "/companies/test-company/contacts", json={"name": "New"}
    )
    assert result == {"contactId": 2}


async def test_request_returns_error_on_404(client, mock_api):
    mock_api.get("/companies/test-company/contacts/999").respond(404, json={"message": "Not found"})
    result = await client.request("GET", "/companies/test-company/contacts/999")
    assert result["error"] is True
    assert result["status_code"] == 404


async def test_request_returns_error_on_405(client, mock_api):
    mock_api.patch("/companies/test-company/contacts/1").respond(
        405, json=[{"message": "Method not allowed"}]
    )
    result = await client.request(
        "PATCH", "/companies/test-company/contacts/1", json={"inactive": True}
    )
    assert result["error"] is True
    assert result["status_code"] == 405


async def test_retry_on_429(client, mock_api):
    route = mock_api.get("/companies/test-company/contacts/1")
    route.side_effect = [
        httpx.Response(429),
        httpx.Response(200, json={"contactId": 1}),
    ]
    result = await client.request("GET", "/companies/test-company/contacts/1")
    assert result == {"contactId": 1}
    assert route.call_count == 2


async def test_retry_gives_up_after_3(client, mock_api):
    mock_api.get("/companies/test-company/contacts/1").respond(429)
    result = await client.request("GET", "/companies/test-company/contacts/1")
    assert result["error"] is True
    assert result["status_code"] == 429


async def test_http_error_returns_error_dict(client, mock_api):
    mock_api.get("/fail").mock(side_effect=httpx.ConnectError("connection refused"))
    result = await client.request("GET", "/fail")
    assert result["error"] is True
    assert result["status_code"] == 0
    assert "connection refused" in result["message"]


async def test_204_returns_empty_dict(client, mock_api):
    mock_api.delete("/companies/test-company/thing/1").respond(204)
    result = await client.request("DELETE", "/companies/test-company/thing/1")
    assert result == {}


# --- Pagination ---


def _paginated_response(data, page, total, page_count):
    return httpx.Response(
        200,
        json=data,
        headers={
            "fiken-api-result-count": str(total),
            "fiken-api-page-count": str(page_count),
            "fiken-api-page": str(page),
            "fiken-api-page-size": str(len(data)),
        },
    )


async def test_paginated_single_page(client, mock_api):
    items = [{"id": 1}, {"id": 2}]
    mock_api.get("/companies/test-company/contacts/").mock(
        return_value=_paginated_response(items, 0, 2, 1)
    )
    result = await client.request_paginated(
        "/companies/test-company/contacts/", page_size=25
    )
    assert result["data"] == items
    assert result["total"] == 2
    assert result["page_count"] == 1


async def test_paginated_fetch_all(client, mock_api):
    route = mock_api.get("/companies/test-company/contacts/")
    route.side_effect = [
        _paginated_response([{"id": 1}], 0, 3, 3),
        _paginated_response([{"id": 2}], 1, 3, 3),
        _paginated_response([{"id": 3}], 2, 3, 3),
    ]
    result = await client.request_paginated(
        "/companies/test-company/contacts/", page_size=1, fetch_all=True
    )
    assert len(result["data"]) == 3
    assert result["fetched_all"] is True
    assert result["total"] == 3


# --- Slug resolution ---


async def test_get_company_slug_cached(client, mock_api):
    slug = await client.get_company_slug()
    assert slug == "test-company"


async def test_get_company_slug_from_api(settings, mock_api):
    settings.company_slug = None
    c = FikenClient(settings)
    mock_api.get("/user/").respond(200, json={"name": "Test User"})
    mock_api.get("/companies/").respond(200, json=[{"slug": "resolved-co"}])
    slug = await c.get_company_slug()
    assert slug == "resolved-co"
    await c.aclose()
