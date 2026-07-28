from datetime import date, timedelta
from typing import Any

from ..client import FikenClient
from .accounts import fiken_account_balances


# Norsk standard kontoplan — klasseinndeling
ASSET_PREFIXES = ("1",)
EQUITY_LIAB_PREFIXES = ("2",)
REVENUE_PREFIXES = ("3",)
EXPENSE_PREFIXES = ("4", "5", "6", "7")
FINANCE_PREFIXES = ("8",)

# Oppstillingsplan etter rekneskapslova § 6-2. To siffer, og 10–19 / 20–29
# dekkjer 1xxx og 2xxx uttømmande, så gruppetotalane summerer seg til klassen.
# Underkontoar ("2380:10001") treffer rett gruppe via startswith.
ASSET_GROUPS = (
    ("anleggsmidler", ("10", "11", "12", "13")),
    ("omlopsmidler", ("14", "15", "16", "17", "18", "19")),
)
EQUITY_LIAB_GROUPS = (
    ("egenkapital", ("20",)),
    ("avsetning_forpliktelser", ("21",)),
    ("langsiktig_gjeld", ("22",)),
    ("kortsiktig_gjeld", ("23", "24", "25", "26", "27", "28", "29")),
)


def _bucket(accounts: list[dict[str, Any]], prefixes: tuple[str, ...]) -> dict[str, Any]:
    matched = [a for a in accounts if a.get("code", "").startswith(prefixes)]
    total = sum(int(a.get("balance", 0)) for a in matched)
    return {"total": total, "accounts": matched}


def _class_with_groups(
    accounts: list[dict[str, Any]],
    prefixes: tuple[str, ...],
    groups: tuple[tuple[str, tuple[str, ...]], ...],
) -> dict[str, Any]:
    """Bøtt ein kontoklasse og del han i undergrupper etter oppstillingsplanen."""
    klass = _bucket(accounts, prefixes)
    klass["groups"] = {name: _bucket(klass["accounts"], pfx) for name, pfx in groups}
    return klass


async def fiken_balance_sheet(
    client: FikenClient,
    date: str,
    *,
    slug: str | None = None,
    include_zero: bool = False,
) -> dict[str, Any]:
    """Balanse per dato (yyyy-MM-dd) — aggregert frå accountBalances.

    Saldoar i øre. `balance_check = sum(eigedelar) + sum(EK_og_gjeld)`. Dette er
    ikkje 0 før årsavslutning, fordi Fiken sine kumulative resultat-kontoar
    (3xxx–8xxx) ikkje er overført til eigenkapitalen. Positivt `balance_check`
    = akkumulert overskot ikkje endå disponert; negativt = akkumulert underskot.

    `assets` og `equity_and_liabilities` har kvar ein `groups`-nøkkel med
    oppdelinga etter rekneskapslova § 6-2 (anleggsmidlar/omløpsmidlar,
    eigenkapital/avsetningar/langsiktig/kortsiktig gjeld).

    `include_zero=False` (standard) held kontoar med saldo 0 utanfor. Dei
    påverkar ingen sum, og dei fleste kontoane i ein kontoplan står i 0.
    """
    res = await fiken_account_balances(client, date, slug=slug, fetch_all=True)
    if isinstance(res, dict) and res.get("error"):
        return res
    accounts = res.get("data", [])
    if not include_zero:
        accounts = [a for a in accounts if int(a.get("balance", 0)) != 0]

    assets = _class_with_groups(accounts, ASSET_PREFIXES, ASSET_GROUPS)
    equity_liab = _class_with_groups(accounts, EQUITY_LIAB_PREFIXES, EQUITY_LIAB_GROUPS)

    return {
        "date": date,
        "currency": "NOK (øre)",
        "assets": assets,
        "equity_and_liabilities": equity_liab,
        "balance_check": assets["total"] + equity_liab["total"],
    }


async def fiken_income_statement(
    client: FikenClient, date_from: str, date_to: str, *, slug: str | None = None
) -> dict[str, Any]:
    """Resultat for periode [date_from, date_to] — aggregert frå accountBalances.

    Fiken sine saldoar er akkumulerte, så periode-saldo = balance(date_to) − balance(date_from−1).
    Inntekter (3xxx) ligg som negative tal (kredit), kostnader (4xxx–7xxx) som positive (debet).
    Netto resultat = −(sum av alle resultatkontoar); positivt tal = overskot.
    """
    try:
        prev_day = (date.fromisoformat(date_from) - timedelta(days=1)).isoformat()
    except ValueError as exc:
        return {
            "error": True,
            "status_code": 400,
            "message": f"Ugyldig date_from '{date_from}': {exc}",
            "fiken_error": None,
        }

    end = await fiken_account_balances(client, date_to, slug=slug, fetch_all=True)
    if isinstance(end, dict) and end.get("error"):
        return end
    start = await fiken_account_balances(client, prev_day, slug=slug, fetch_all=True)
    if isinstance(start, dict) and start.get("error"):
        return start

    start_by_code = {a["code"]: int(a.get("balance", 0)) for a in start.get("data", [])}

    period_accounts: list[dict[str, Any]] = []
    for a in end.get("data", []):
        code = a.get("code", "")
        if not code.startswith(REVENUE_PREFIXES + EXPENSE_PREFIXES + FINANCE_PREFIXES):
            continue
        end_bal = int(a.get("balance", 0))
        start_bal = start_by_code.get(code, 0)
        period_bal = end_bal - start_bal
        if period_bal == 0:
            continue
        period_accounts.append({"code": code, "name": a.get("name"), "balance": period_bal})

    revenue = _bucket(period_accounts, REVENUE_PREFIXES)
    expenses = _bucket(period_accounts, EXPENSE_PREFIXES)
    finance = _bucket(period_accounts, FINANCE_PREFIXES)

    net_result = -(revenue["total"] + expenses["total"] + finance["total"])

    return {
        "date_from": date_from,
        "date_to": date_to,
        "currency": "NOK (øre)",
        "revenue": revenue,
        "expenses": expenses,
        "finance": finance,
        "net_result": net_result,
    }
