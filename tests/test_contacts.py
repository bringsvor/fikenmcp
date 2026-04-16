import httpx
import respx

from fiken_mcp.tools.contacts import (
    fiken_contacts_list,
    fiken_contact_get,
    fiken_contact_create,
    fiken_contact_update,
)

SLUG = "test-company"
CONTACT = {
    "contactId": 100,
    "createdDate": "2023-01-01",
    "lastModifiedDate": "2024-01-01",
    "name": "Acme AS",
    "email": "acme@example.com",
    "organizationNumber": "123456789",
    "customer": True,
    "supplier": False,
    "inactive": False,
    "contactPerson": [],
    "customerAccountCode": "1500:10001",
    "supplierAccountCode": None,
    "notes": [],
    "currency": "NOK",
    "language": "Norwegian",
    "address": {"streetAddress": "Gate 1", "city": "OSLO", "postCode": "0001", "country": "Norge"},
}


def _list_response(data, total=None):
    total = total or len(data)
    return httpx.Response(
        200,
        json=data,
        headers={
            "fiken-api-result-count": str(total),
            "fiken-api-page-count": "1",
        },
    )


# --- List ---


async def test_contacts_list(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/contacts/").mock(
        return_value=_list_response([CONTACT])
    )
    result = await fiken_contacts_list(client, slug=SLUG)
    assert len(result["data"]) == 1
    assert result["data"][0]["name"] == "Acme AS"


# --- Get ---


async def test_contact_get(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/contacts/100").respond(200, json=CONTACT)
    result = await fiken_contact_get(client, 100, slug=SLUG)
    assert result["contactId"] == 100
    assert result["name"] == "Acme AS"


# --- Create ---


async def test_contact_create_dry_run(client, mock_api):
    result = await fiken_contact_create(
        client, name="New Co", customer=True, slug=SLUG
    )
    assert result["dry_run"] is True
    assert "POST" in result["operation"]
    assert result["payload"]["name"] == "New Co"


async def test_contact_create_confirm(client, mock_api):
    mock_api.post(f"/companies/{SLUG}/contacts").respond(
        201, json={"contactId": 200}
    )
    result = await fiken_contact_create(
        client, name="New Co", customer=True, slug=SLUG, confirm=True
    )
    assert result == {"contactId": 200}


# --- Update (PUT read-modify-write) ---


async def test_contact_update_dry_run(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/contacts/100").respond(200, json=CONTACT)
    result = await fiken_contact_update(client, 100, inactive=True, slug=SLUG)
    assert result["dry_run"] is True
    assert "PUT" in result["operation"]
    assert result["payload"] == {"inactive": True}


async def test_contact_update_confirm_sends_put(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/contacts/100").respond(200, json=CONTACT)
    put_route = mock_api.put(f"/companies/{SLUG}/contacts/100").respond(200, json={})

    result = await fiken_contact_update(
        client, 100, inactive=True, slug=SLUG, confirm=True
    )
    assert result == {}

    sent = put_route.calls[0].request
    assert sent.method == "PUT"


async def test_contact_update_strips_readonly_fields(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/contacts/100").respond(200, json=CONTACT)
    put_route = mock_api.put(f"/companies/{SLUG}/contacts/100").respond(200, json={})

    await fiken_contact_update(
        client, 100, inactive=True, slug=SLUG, confirm=True
    )

    import json
    body = json.loads(put_route.calls[0].request.content)
    for key in ("contactId", "createdDate", "lastModifiedDate", "contactPerson", "customerAccountCode", "supplierAccountCode"):
        assert key not in body, f"Read-only field {key} should be stripped"


async def test_contact_update_merges_with_current(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/contacts/100").respond(200, json=CONTACT)
    put_route = mock_api.put(f"/companies/{SLUG}/contacts/100").respond(200, json={})

    await fiken_contact_update(
        client, 100, name="Renamed AS", slug=SLUG, confirm=True
    )

    import json
    body = json.loads(put_route.calls[0].request.content)
    assert body["name"] == "Renamed AS"
    assert body["email"] == "acme@example.com"  # preserved from GET
    assert body["inactive"] is False  # preserved from GET


async def test_contact_update_no_fields_returns_error(client, mock_api):
    result = await fiken_contact_update(client, 100, slug=SLUG)
    assert result["error"] is True
    assert result["status_code"] == 400


async def test_contact_update_propagates_get_error(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/contacts/100").respond(404, json={"message": "Not found"})
    result = await fiken_contact_update(
        client, 100, inactive=True, slug=SLUG, confirm=True
    )
    assert result["error"] is True
    assert result["status_code"] == 404
