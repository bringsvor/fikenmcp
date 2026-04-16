import httpx

from fiken_mcp.tools.invoices import (
    fiken_invoices_list,
    fiken_invoice_get,
    fiken_invoice_create,
    fiken_invoice_send,
)

SLUG = "test-company"


def _list_response(data):
    return httpx.Response(
        200,
        json=data,
        headers={"fiken-api-result-count": str(len(data)), "fiken-api-page-count": "1"},
    )


# --- List & Get ---


async def test_invoices_list(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/invoices/").mock(
        return_value=_list_response([{"invoiceId": 1}])
    )
    result = await fiken_invoices_list(client, slug=SLUG)
    assert len(result["data"]) == 1


async def test_invoice_get(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/invoices/42").respond(200, json={"invoiceId": 42})
    result = await fiken_invoice_get(client, 42, slug=SLUG)
    assert result["invoiceId"] == 42


# --- Create dry-run: gross calculation ---


async def test_invoice_create_dry_run_with_unit_price(client, mock_api):
    result = await fiken_invoice_create(
        client,
        customer_id=1,
        issue_date="2026-04-16",
        due_date="2026-05-16",
        lines=[{"description": "Timar", "unitPrice": 150000, "quantity": 10, "vatType": "HIGH", "incomeAccount": "3000"}],
        bank_account_code="1920",
        slug=SLUG,
    )
    assert result["dry_run"] is True
    assert "1500000 øre" in result["summary"]
    assert "15000.00 NOK" in result["summary"]


async def test_invoice_create_dry_run_with_net_price(client, mock_api):
    result = await fiken_invoice_create(
        client,
        customer_id=1,
        issue_date="2026-04-16",
        due_date="2026-05-16",
        lines=[{"description": "Vare", "netPrice": 100000, "vat": 25000, "vatType": "HIGH", "incomeAccount": "3000"}],
        bank_account_code="1920",
        slug=SLUG,
    )
    assert result["dry_run"] is True
    assert "125000 øre" in result["summary"]


async def test_invoice_create_confirm(client, mock_api):
    mock_api.post(f"/companies/{SLUG}/invoices").respond(201, json={"invoiceId": 99})
    result = await fiken_invoice_create(
        client,
        customer_id=1,
        issue_date="2026-04-16",
        due_date="2026-05-16",
        lines=[{"description": "X", "netPrice": 1000, "vat": 250}],
        bank_account_code="1920",
        slug=SLUG,
        confirm=True,
    )
    assert result == {"invoiceId": 99}


# --- Send ---


async def test_invoice_send_dry_run(client, mock_api):
    result = await fiken_invoice_send(
        client, 42, method="email", email_address="test@example.com", slug=SLUG
    )
    assert result["dry_run"] is True
    assert "email" in result["summary"]
    assert "test@example.com" in result["summary"]


async def test_invoice_send_confirm(client, mock_api):
    mock_api.post(f"/companies/{SLUG}/sendInvoice").respond(200, json={})
    result = await fiken_invoice_send(
        client, 42, method="email", email_address="test@example.com", slug=SLUG, confirm=True
    )
    assert result == {}
