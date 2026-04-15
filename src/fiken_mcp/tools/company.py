from typing import Any

from ..client import FikenClient


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
