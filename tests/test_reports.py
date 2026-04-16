import httpx

from fiken_mcp.tools.reports import fiken_balance_sheet, fiken_income_statement

SLUG = "test-company"


def _balances_response(data):
    return httpx.Response(
        200,
        json=data,
        headers={"fiken-api-result-count": str(len(data)), "fiken-api-page-count": "1"},
    )


# --- Balance sheet ---


async def test_balance_sheet(client, mock_api):
    balances = [
        {"code": "1920", "name": "Bank", "balance": 5000000},
        {"code": "1500", "name": "Kundefordringar", "balance": 1000000},
        {"code": "2020", "name": "Aksjekapital", "balance": -3000000},
        {"code": "2400", "name": "Leverandørgjeld", "balance": -500000},
        {"code": "3000", "name": "Salgsinntekt", "balance": -2000000},  # P&L, ikkje med i balanse
    ]
    mock_api.get(f"/companies/{SLUG}/accountBalances").mock(
        return_value=_balances_response(balances)
    )
    result = await fiken_balance_sheet(client, "2026-04-16", slug=SLUG)

    assert result["date"] == "2026-04-16"
    assert result["assets"]["total"] == 6000000  # 5M + 1M
    assert result["equity_and_liabilities"]["total"] == -3500000  # -3M + -0.5M
    assert result["balance_check"] == 2500000  # 6M + (-3.5M) = 2.5M (ufordelt resultat)
    assert len(result["assets"]["accounts"]) == 2
    assert len(result["equity_and_liabilities"]["accounts"]) == 2


async def test_balance_sheet_propagates_error(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/accountBalances").respond(
        401, json={"message": "Unauthorized"}
    )
    result = await fiken_balance_sheet(client, "2026-04-16", slug=SLUG)
    assert result["error"] is True


# --- Income statement ---


async def test_income_statement(client, mock_api):
    end_balances = [
        {"code": "1920", "name": "Bank", "balance": 5000000},  # ikkje P&L
        {"code": "3000", "name": "Salgsinntekt", "balance": -2000000},
        {"code": "4000", "name": "Varekostnad", "balance": 800000},
        {"code": "6300", "name": "Leige", "balance": 300000},
        {"code": "8050", "name": "Aksjeutbytte", "balance": -100000},
    ]
    start_balances = [
        {"code": "1920", "name": "Bank", "balance": 4000000},
        {"code": "3000", "name": "Salgsinntekt", "balance": -1500000},
        {"code": "4000", "name": "Varekostnad", "balance": 600000},
        {"code": "6300", "name": "Leige", "balance": 200000},
        {"code": "8050", "name": "Aksjeutbytte", "balance": -50000},
    ]

    route = mock_api.get(f"/companies/{SLUG}/accountBalances")
    route.side_effect = [
        _balances_response(end_balances),    # date_to
        _balances_response(start_balances),  # prev_day
    ]

    result = await fiken_income_statement(
        client, "2026-01-01", "2026-04-16", slug=SLUG
    )

    assert result["date_from"] == "2026-01-01"
    assert result["date_to"] == "2026-04-16"

    # Period deltas: 3000: -500000, 4000: +200000, 6300: +100000, 8050: -50000
    assert result["revenue"]["total"] == -500000  # 3xxx
    assert result["expenses"]["total"] == 300000  # 4xxx + 6xxx
    assert result["finance"]["total"] == -50000   # 8xxx

    # net_result = -(revenue + expenses + finance) = -(-500000 + 300000 + -50000) = 250000
    assert result["net_result"] == 250000


async def test_income_statement_invalid_date():
    from fiken_mcp.config import Settings
    from fiken_mcp.client import FikenClient

    settings = Settings(api_token="x", company_slug="co")
    c = FikenClient(settings)
    result = await fiken_income_statement(c, "not-a-date", "2026-04-16", slug="co")
    assert result["error"] is True
    assert "Ugyldig" in result["message"]
    await c.aclose()


async def test_income_statement_zero_balance_excluded(client, mock_api):
    end_balances = [
        {"code": "3000", "name": "Salg", "balance": -1000000},
        {"code": "4000", "name": "Varekost", "balance": 500000},
    ]
    start_balances = [
        {"code": "3000", "name": "Salg", "balance": -1000000},  # same → delta 0 → excluded
        {"code": "4000", "name": "Varekost", "balance": 300000},
    ]
    route = mock_api.get(f"/companies/{SLUG}/accountBalances")
    route.side_effect = [
        _balances_response(end_balances),
        _balances_response(start_balances),
    ]
    result = await fiken_income_statement(
        client, "2026-01-01", "2026-04-16", slug=SLUG
    )
    # 3000 has 0 delta, should be excluded
    assert result["revenue"]["total"] == 0
    assert len(result["revenue"]["accounts"]) == 0
    # 4000 has +200000 delta
    assert result["expenses"]["total"] == 200000
