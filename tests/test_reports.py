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


# --- Balance sheet grouping (rekneskapslova § 6-2) ---


GROUPED_BALANCES = [
    {"code": "1200", "name": "Maskiner", "balance": 4000000},          # anleggsmidlar
    {"code": "1500", "name": "Kundefordringar", "balance": 1000000},   # omløpsmidlar
    {"code": "1920:10001", "name": "Folio", "balance": 500000},        # omløpsmidlar, underkonto
    {"code": "2020", "name": "Aksjekapital", "balance": -3000000},     # eigenkapital
    {"code": "2120", "name": "Utsett skatt", "balance": -200000},      # avsetning
    {"code": "2250", "name": "Gjeld til eigar", "balance": -1500000},  # langsiktig
    {"code": "2380:10001", "name": "Kassakreditt", "balance": -800000},  # kortsiktig, underkonto
    {"code": "2400", "name": "Leverandørgjeld", "balance": -500000},   # kortsiktig
]


async def test_balance_sheet_groups(client, mock_api):
    """Kontoklassane er delte etter oppstillingsplanen, og underkontoar treffer rett gruppe."""
    mock_api.get(f"/companies/{SLUG}/accountBalances").mock(
        return_value=_balances_response(GROUPED_BALANCES)
    )
    result = await fiken_balance_sheet(client, "2026-04-16", slug=SLUG)

    ag = result["assets"]["groups"]
    assert ag["anleggsmidler"]["total"] == 4000000
    assert ag["omlopsmidler"]["total"] == 1500000  # 1500 + underkonto 1920:10001

    eg = result["equity_and_liabilities"]["groups"]
    assert eg["egenkapital"]["total"] == -3000000
    assert eg["avsetning_forpliktelser"]["total"] == -200000
    assert eg["langsiktig_gjeld"]["total"] == -1500000
    assert eg["kortsiktig_gjeld"]["total"] == -1300000  # underkonto 2380:10001 + 2400

    # Underkontoen med kolon må hamne i kortsiktig, ikkje falle utanfor
    assert [a["code"] for a in eg["kortsiktig_gjeld"]["accounts"]] == ["2380:10001", "2400"]


async def test_balance_sheet_groups_sum_to_class_total(client, mock_api):
    """Ingen kontokode skal falle utanfor alle grupper."""
    mock_api.get(f"/companies/{SLUG}/accountBalances").mock(
        return_value=_balances_response(GROUPED_BALANCES)
    )
    result = await fiken_balance_sheet(client, "2026-04-16", slug=SLUG)

    for klass in ("assets", "equity_and_liabilities"):
        groups = result[klass]["groups"].values()
        assert sum(g["total"] for g in groups) == result[klass]["total"]
        assert sum(len(g["accounts"]) for g in groups) == len(result[klass]["accounts"])


async def test_balance_sheet_zero_accounts_excluded_by_default(client, mock_api):
    """Nullsaldoar er støy i ein balanse, men skal ikkje endre nokon sum."""
    balances = [
        {"code": "1920", "name": "Bank", "balance": 5000000},
        {"code": "2241", "name": "AVSLUTTA Lån", "balance": 0},
        {"code": "2020", "name": "Aksjekapital", "balance": -3000000},
    ]
    route = mock_api.get(f"/companies/{SLUG}/accountBalances")
    route.side_effect = [_balances_response(balances), _balances_response(balances)]

    default = await fiken_balance_sheet(client, "2026-04-16", slug=SLUG)
    with_zero = await fiken_balance_sheet(
        client, "2026-04-16", slug=SLUG, include_zero=True
    )

    assert [a["code"] for a in default["equity_and_liabilities"]["accounts"]] == ["2020"]
    assert "2241" in [a["code"] for a in with_zero["equity_and_liabilities"]["accounts"]]
    assert with_zero["equity_and_liabilities"]["groups"]["langsiktig_gjeld"]["total"] == 0

    # Filtreringa er reint kosmetisk — alle summar skal vere identiske
    for key in ("balance_check",):
        assert default[key] == with_zero[key]
    for klass in ("assets", "equity_and_liabilities"):
        assert default[klass]["total"] == with_zero[klass]["total"]


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
