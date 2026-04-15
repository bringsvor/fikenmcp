from typing import Any

from ..client import FikenClient, DEFAULT_PAGE_SIZE


async def fiken_companies_list(
    client: FikenClient,
    *,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict[str, Any]:
    """List alle selskap brukaren har tilgang til."""
    return await client.request_paginated(
        "/companies/", page=page, page_size=page_size, fetch_all=fetch_all
    )


async def fiken_company_get(client: FikenClient, slug: str | None = None) -> dict[str, Any]:
    """Hent innlogga brukar og selskapsinfo."""
    user = await client.request("GET", "/user/")
    if isinstance(user, dict) and user.get("error"):
        return user

    resolved_slug = slug or await client.get_company_slug()
    if isinstance(resolved_slug, dict) and resolved_slug.get("error"):
        return resolved_slug

    company = await client.request("GET", f"/companies/{resolved_slug}")
    if isinstance(company, dict) and company.get("error"):
        return company

    return {"user": user, "company": company}
