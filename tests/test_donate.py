import httpx

from fiken_mcp.tools.donate import fiken_donate, STRIPE_LINK, BRINGSVOR

SLUG = "test-company"
DONOR_COMPANY = {"name": "Testselskap AS", "organizationNumber": "987654321"}


def _mock_company(mock_api):
    mock_api.get(f"/companies/{SLUG}").respond(200, json=DONOR_COMPANY)


def _list_response(data):
    return httpx.Response(
        200,
        json=data,
        headers={"fiken-api-result-count": str(len(data)), "fiken-api-page-count": "1"},
    )


# --- Stripe ---


async def test_donate_stripe(client, mock_api):
    result = await fiken_donate(client, method="stripe", slug=SLUG)
    assert result["method"] == "stripe"
    assert result["payment_link"] == STRIPE_LINK
    assert "500 NOK" in result["amount_suggestion"]


async def test_donate_stripe_custom_amount(client, mock_api):
    result = await fiken_donate(client, method="stripe", amount=1000, slug=SLUG)
    assert "1000 NOK" in result["amount_suggestion"]


async def test_donate_invalid_method(client, mock_api):
    result = await fiken_donate(client, method="vipps", slug=SLUG)
    assert result["error"] is True
    assert "vipps" in result["message"]


# --- Fiken: kontakt finst ikkje ---


async def test_donate_fiken_dry_run_new_contact(client, mock_api):
    _mock_company(mock_api)
    mock_api.get(f"/companies/{SLUG}/contacts/").mock(
        return_value=_list_response([])
    )
    result = await fiken_donate(client, method="fiken", amount=500, slug=SLUG)
    assert result["dry_run"] is True
    assert "Bringsvor Consulting AS" in result["summary"]
    assert "500 NOK" in result["summary"]
    assert "steps" in result


# --- Fiken: kontakt finst ---


EXISTING_BRINGSVOR = {
    "contactId": 99,
    "name": "Bringsvor Consulting AS",
    "organizationNumber": "996835243",
    "supplier": True,
}


async def test_donate_fiken_dry_run_existing_contact(client, mock_api):
    _mock_company(mock_api)
    mock_api.get(f"/companies/{SLUG}/contacts/").mock(
        return_value=_list_response([EXISTING_BRINGSVOR])
    )
    result = await fiken_donate(client, method="fiken", amount=750, slug=SLUG)
    assert result["dry_run"] is True
    assert "750 NOK" in result["summary"]
    assert result["payload"]["supplierId"] == 99


async def test_donate_fiken_confirm_existing_contact(client, mock_api):
    _mock_company(mock_api)
    mock_api.get(f"/companies/{SLUG}/contacts/").mock(
        return_value=_list_response([EXISTING_BRINGSVOR])
    )
    mock_api.post(f"/companies/{SLUG}/purchases").respond(
        201, json={}, headers={"Location": "/purchases/10"}
    )
    result = await fiken_donate(
        client, method="fiken", amount=500, slug=SLUG, confirm=True
    )
    assert result == {}


async def test_donate_fiken_confirm_creates_contact_and_purchase(client, mock_api):
    _mock_company(mock_api)
    mock_api.get(f"/companies/{SLUG}/contacts/").mock(
        return_value=_list_response([])
    )
    mock_api.post(f"/companies/{SLUG}/contacts").respond(
        201, json={"contactId": 200}
    )
    mock_api.post(f"/companies/{SLUG}/purchases").respond(
        201, json={}, headers={"Location": "/purchases/11"}
    )
    result = await fiken_donate(
        client, method="fiken", amount=500, slug=SLUG, confirm=True
    )
    assert result == {}


async def test_donate_fiken_includes_donor_info_from_company(client, mock_api):
    mock_api.get(f"/companies/{SLUG}").respond(
        200, json={"name": "Acme AS", "organizationNumber": "123456789"}
    )
    mock_api.get(f"/companies/{SLUG}/contacts/").mock(
        return_value=_list_response([EXISTING_BRINGSVOR])
    )
    result = await fiken_donate(client, method="fiken", amount=500, slug=SLUG)
    assert result["dry_run"] is True
    desc = result["payload"]["lines"][0]["description"]
    assert "Acme AS" in desc
    assert "123456789" in desc
    assert result["payload"]["identifier"] == "123456789"


async def test_donate_fiken_graceful_without_company_info(client, mock_api):
    mock_api.get(f"/companies/{SLUG}").respond(404)
    mock_api.get(f"/companies/{SLUG}/contacts/").mock(
        return_value=_list_response([EXISTING_BRINGSVOR])
    )
    result = await fiken_donate(client, method="fiken", slug=SLUG)
    assert result["dry_run"] is True
    desc = result["payload"]["lines"][0]["description"]
    assert desc == "Støtte til Fiken MCP-prosjektet"
    assert "identifier" not in result["payload"]
