import httpx

from fiken_mcp.tools.credit_notes import (
    fiken_credit_notes_list,
    fiken_credit_note_get,
    fiken_credit_note_create_full,
    fiken_credit_note_create_partial,
    fiken_credit_note_set_counter,
    fiken_credit_note_send,
)

SLUG = "test-company"

CREDIT_NOTE = {
    "creditNoteId": 1,
    "creditNoteNumber": 5001,
    "net": 100000,
    "vat": 25000,
    "gross": 125000,
    "netInNok": 100000,
    "vatInNok": 25000,
    "grossInNok": 125000,
    "issueDate": "2026-04-16",
    "settled": False,
    "associatedInvoiceId": 42,
    "customer": {"contactId": 100, "name": "Acme AS"},
    "lines": [{"unitPrice": 100000, "quantity": 1, "vatType": "HIGH"}],
}


def _list_response(data):
    return httpx.Response(
        200,
        json=data,
        headers={"fiken-api-result-count": str(len(data)), "fiken-api-page-count": "1"},
    )


# --- List ---


async def test_credit_notes_list(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/creditNotes").mock(
        return_value=_list_response([CREDIT_NOTE])
    )
    result = await fiken_credit_notes_list(client, slug=SLUG)
    assert len(result["data"]) == 1
    assert result["data"][0]["creditNoteId"] == 1


async def test_credit_notes_list_with_filters(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/creditNotes").mock(
        return_value=_list_response([CREDIT_NOTE])
    )
    result = await fiken_credit_notes_list(
        client, slug=SLUG, settled=False, customer_id=100
    )
    assert len(result["data"]) == 1


# --- Get ---


async def test_credit_note_get(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/creditNotes/1").respond(200, json=CREDIT_NOTE)
    result = await fiken_credit_note_get(client, 1, slug=SLUG)
    assert result["creditNoteId"] == 1
    assert result["gross"] == 125000


# --- Create full ---


async def test_credit_note_create_full_dry_run(client, mock_api):
    result = await fiken_credit_note_create_full(
        client, invoice_id=42, issue_date="2026-04-16", slug=SLUG
    )
    assert result["dry_run"] is True
    assert "full kreditnota" in result["summary"]
    assert "faktura 42" in result["summary"]
    assert result["payload"]["invoiceId"] == 42


async def test_credit_note_create_full_confirm(client, mock_api):
    mock_api.post(f"/companies/{SLUG}/creditNotes/full").respond(
        201, json={}, headers={"Location": "/creditNotes/2"}
    )
    result = await fiken_credit_note_create_full(
        client, invoice_id=42, issue_date="2026-04-16", slug=SLUG, confirm=True
    )
    assert result == {}


# --- Create partial ---


async def test_credit_note_create_partial_dry_run(client, mock_api):
    lines = [{"unitPrice": 50000, "quantity": 2, "vatType": "HIGH", "description": "Retur"}]
    result = await fiken_credit_note_create_partial(
        client, issue_date="2026-04-16", lines=lines, invoice_id=42, slug=SLUG
    )
    assert result["dry_run"] is True
    assert "delvis kreditnota" in result["summary"]
    assert "100000 øre" in result["summary"]
    assert "1000.00 NOK" in result["summary"]


async def test_credit_note_create_partial_confirm(client, mock_api):
    mock_api.post(f"/companies/{SLUG}/creditNotes/partial").respond(
        201, json={}, headers={"Location": "/creditNotes/3"}
    )
    lines = [{"unitPrice": 50000, "quantity": 1}]
    result = await fiken_credit_note_create_partial(
        client, issue_date="2026-04-16", lines=lines, contact_id=100,
        slug=SLUG, confirm=True
    )
    assert result == {}


async def test_credit_note_create_partial_no_invoice_no_contact(client, mock_api):
    lines = [{"unitPrice": 10000, "quantity": 1}]
    result = await fiken_credit_note_create_partial(
        client, issue_date="2026-04-16", lines=lines, slug=SLUG
    )
    assert result["dry_run"] is True
    assert "ukjent" in result["summary"]


# --- Set counter ---


async def test_credit_note_set_counter_dry_run(client, mock_api):
    result = await fiken_credit_note_set_counter(client, slug=SLUG)
    assert result["dry_run"] is True
    assert "20001" in result["summary"]
    assert result["payload"]["value"] == 20001


async def test_credit_note_set_counter_confirm(client, mock_api):
    mock_api.post(f"/companies/{SLUG}/creditNotes/counter").respond(204)
    result = await fiken_credit_note_set_counter(
        client, value=30001, slug=SLUG, confirm=True
    )
    assert result == {}


# --- Send ---


async def test_credit_note_send_dry_run(client, mock_api):
    result = await fiken_credit_note_send(
        client, 1, method="email", email_address="test@example.com", slug=SLUG
    )
    assert result["dry_run"] is True
    assert "kreditnota 1" in result["summary"]
    assert "test@example.com" in result["summary"]


async def test_credit_note_send_confirm(client, mock_api):
    mock_api.post(f"/companies/{SLUG}/creditNotes/send").respond(200, json={})
    result = await fiken_credit_note_send(
        client, 1, method="email", email_address="test@example.com",
        slug=SLUG, confirm=True
    )
    assert result == {}
