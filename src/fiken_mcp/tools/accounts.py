from typing import Any

from ..client import FikenClient, DEFAULT_PAGE_SIZE


async def _slug(client: FikenClient, slug: str | None) -> str | dict[str, Any]:
    return slug or await client.get_company_slug()


async def fiken_accounts_list(
    client: FikenClient,
    *,
    slug: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict[str, Any]:
    """Full kontoplan — kontonummer og namn."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    return await client.request_paginated(
        f"/companies/{resolved}/accounts/",
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )


async def fiken_account_balances(
    client: FikenClient,
    date: str,
    *,
    slug: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = True,
) -> dict[str, Any]:
    """Saldo per konto per dato (yyyy-MM-dd). Hentar alle sider som standard."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    return await client.request_paginated(
        f"/companies/{resolved}/accountBalances",
        params={"date": date},
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )


async def fiken_account_balance_get(
    client: FikenClient,
    account_code: str,
    date: str,
    *,
    slug: str | None = None,
) -> dict[str, Any]:
    """Saldo for éin konto på gitt dato (t.d. '2270' for marginlån)."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    return await client.request(
        "GET",
        f"/companies/{resolved}/accountBalances/{account_code}",
        params={"date": date},
    )
