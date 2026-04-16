import httpx

from fiken_mcp.tools.company import fiken_companies_list, fiken_company_get

SLUG = "test-company"

COMPANY = {"slug": SLUG, "name": "Test Company AS", "organizationNumber": "123456789"}
USER = {"name": "Test Brukar", "email": "test@example.com"}


def _list_response(data):
    return httpx.Response(
        200,
        json=data,
        headers={"fiken-api-result-count": str(len(data)), "fiken-api-page-count": "1"},
    )


async def test_companies_list(client, mock_api):
    mock_api.get("/companies/").mock(return_value=_list_response([COMPANY]))
    result = await fiken_companies_list(client)
    assert len(result["data"]) == 1
    assert result["data"][0]["slug"] == SLUG


async def test_company_get(client, mock_api):
    mock_api.get("/user/").respond(200, json=USER)
    mock_api.get(f"/companies/{SLUG}").respond(200, json=COMPANY)
    result = await fiken_company_get(client, slug=SLUG)
    assert result["user"]["name"] == "Test Brukar"
    assert result["company"]["slug"] == SLUG


async def test_company_get_propagates_user_error(client, mock_api):
    mock_api.get("/user/").respond(401, json={"message": "Unauthorized"})
    result = await fiken_company_get(client, slug=SLUG)
    assert result["error"] is True
    assert result["status_code"] == 401
