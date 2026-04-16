import httpx

from fiken_mcp.tools.accounts import (
    fiken_accounts_list,
    fiken_account_balances,
    fiken_account_balance_get,
)

SLUG = "test-company"


def _list_response(data):
    return httpx.Response(
        200,
        json=data,
        headers={"fiken-api-result-count": str(len(data)), "fiken-api-page-count": "1"},
    )


async def test_accounts_list(client, mock_api):
    accounts = [{"code": "1920", "name": "Bank"}, {"code": "3000", "name": "Salgsinntekt"}]
    mock_api.get(f"/companies/{SLUG}/accounts/").mock(
        return_value=_list_response(accounts)
    )
    result = await fiken_accounts_list(client, slug=SLUG)
    assert len(result["data"]) == 2
    assert result["data"][0]["code"] == "1920"


async def test_account_balances(client, mock_api):
    balances = [
        {"code": "1920", "name": "Bank", "balance": 5000000},
        {"code": "2020", "name": "Aksjekapital", "balance": -3000000},
    ]
    mock_api.get(f"/companies/{SLUG}/accountBalances").mock(
        return_value=_list_response(balances)
    )
    result = await fiken_account_balances(client, "2026-04-16", slug=SLUG)
    assert len(result["data"]) == 2
    assert result["fetched_all"] is True


async def test_account_balance_get(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/accountBalances/1920").respond(
        200, json={"code": "1920", "name": "Bank", "balance": 5000000}
    )
    result = await fiken_account_balance_get(client, "1920", "2026-04-16", slug=SLUG)
    assert result["code"] == "1920"
    assert result["balance"] == 5000000
