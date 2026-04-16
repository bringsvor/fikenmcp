from typing import Any

from ..client import FikenClient, DEFAULT_PAGE_SIZE


async def _slug(client: FikenClient, slug: str | None) -> str | dict[str, Any]:
    return slug or await client.get_company_slug()


async def fiken_inbox_list(
    client: FikenClient,
    *,
    slug: str | None = None,
    status: str | None = None,
    name: str | None = None,
    sort_by: str | None = None,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    fetch_all: bool = False,
) -> dict[str, Any]:
    """List dokument i innboksen.

    `sort_by`: 'createdDate asc', 'createdDate desc', 'name asc', 'name desc'.
    `status`: filter på dokumentstatus.
    """
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    params: dict[str, Any] = {}
    if status is not None:
        params["status"] = status
    if name is not None:
        params["name"] = name
    if sort_by is not None:
        params["sortBy"] = sort_by

    return await client.request_paginated(
        f"/companies/{resolved}/inbox",
        params=params,
        page=page,
        page_size=page_size,
        fetch_all=fetch_all,
    )
