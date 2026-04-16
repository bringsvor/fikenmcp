import httpx

from fiken_mcp.tools.inbox import fiken_inbox_list

SLUG = "test-company"


def _list_response(data):
    return httpx.Response(
        200,
        json=data,
        headers={"fiken-api-result-count": str(len(data)), "fiken-api-page-count": "1"},
    )


async def test_inbox_list(client, mock_api):
    docs = [
        {"name": "faktura.pdf", "status": "new", "createdDate": "2026-04-10"},
        {"name": "kvittering.pdf", "status": "new", "createdDate": "2026-04-12"},
    ]
    mock_api.get(f"/companies/{SLUG}/inbox").mock(
        return_value=_list_response(docs)
    )
    result = await fiken_inbox_list(client, slug=SLUG)
    assert len(result["data"]) == 2
    assert result["data"][0]["name"] == "faktura.pdf"


async def test_inbox_list_with_filters(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/inbox").mock(
        return_value=_list_response([{"name": "test.pdf", "status": "new"}])
    )
    result = await fiken_inbox_list(
        client, slug=SLUG, status="new", sort_by="createdDate desc"
    )
    assert len(result["data"]) == 1


async def test_inbox_list_empty(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/inbox").mock(
        return_value=_list_response([])
    )
    result = await fiken_inbox_list(client, slug=SLUG)
    assert result["data"] == []
    assert result["total"] == 0
