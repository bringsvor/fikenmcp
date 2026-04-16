import httpx

from fiken_mcp.tools.bank import (
    fiken_bank_accounts_list,
    fiken_bank_account_get,
    fiken_bank_transactions,
)

SLUG = "test-company"

BANK_ACCOUNT = {
    "bankAccountId": 10,
    "name": "Driftskonto",
    "accountCode": "1920:10001",
    "reconciledBalance": 5000000,
    "reconciledDate": "2026-04-15",
}


def _list_response(data):
    return httpx.Response(
        200,
        json=data,
        headers={"fiken-api-result-count": str(len(data)), "fiken-api-page-count": "1"},
    )


async def test_bank_accounts_list(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/bankAccounts").mock(
        return_value=_list_response([BANK_ACCOUNT])
    )
    result = await fiken_bank_accounts_list(client, slug=SLUG)
    assert len(result["data"]) == 1
    assert result["data"][0]["name"] == "Driftskonto"


async def test_bank_account_get(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/bankAccounts/10").respond(200, json=BANK_ACCOUNT)
    result = await fiken_bank_account_get(client, 10, slug=SLUG)
    assert result["bankAccountId"] == 10
    assert result["accountCode"] == "1920:10001"


async def test_bank_transactions_happy_path(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/bankAccounts/10").respond(200, json=BANK_ACCOUNT)

    journal_entries = [
        {
            "journalEntryId": 1,
            "journalEntryNumber": 100,
            "date": "2026-03-15",
            "description": "Husleige",
            "lines": [
                {"account": "1920:10001", "amount": -50000},
                {"account": "6300", "amount": 50000},
            ],
        },
        {
            "journalEntryId": 2,
            "journalEntryNumber": 101,
            "date": "2026-03-20",
            "description": "Kundebetaling",
            "lines": [
                {"account": "1920:10001", "amount": 100000},
                {"account": "1500", "amount": -100000},
            ],
        },
    ]
    mock_api.get(f"/companies/{SLUG}/journalEntries").mock(
        return_value=_list_response(journal_entries)
    )

    result = await fiken_bank_transactions(
        client, 10, "2026-03-01", "2026-03-31", slug=SLUG
    )
    assert result["bank_account_id"] == 10
    assert result["bank_account_code"] == "1920:10001"
    assert result["transaction_count"] == 2
    assert result["net_amount"] == 50000  # -50000 + 100000

    # Sorted by date
    assert result["transactions"][0]["description"] == "Husleige"
    assert result["transactions"][0]["amount"] == -50000
    assert result["transactions"][0]["counterpart_accounts"] == ["6300"]

    assert result["transactions"][1]["description"] == "Kundebetaling"
    assert result["transactions"][1]["amount"] == 100000


async def test_bank_transactions_propagates_account_error(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/bankAccounts/99").respond(
        404, json={"message": "Not found"}
    )
    result = await fiken_bank_transactions(
        client, 99, "2026-03-01", "2026-03-31", slug=SLUG
    )
    assert result["error"] is True
    assert result["status_code"] == 404


async def test_bank_transactions_missing_account_code(client, mock_api):
    bad_account = {**BANK_ACCOUNT, "accountCode": None}
    mock_api.get(f"/companies/{SLUG}/bankAccounts/10").respond(200, json=bad_account)
    result = await fiken_bank_transactions(
        client, 10, "2026-03-01", "2026-03-31", slug=SLUG
    )
    assert result["error"] is True
    assert "accountCode" in result["message"]
