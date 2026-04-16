import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger("fiken_mcp.client")

from .config import Settings

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


class FikenClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self._semaphore = asyncio.Semaphore(1)
        self._http = httpx.AsyncClient(
            base_url=self.settings.base_url,
            headers={
                "Authorization": f"Bearer {self.settings.api_token}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )
        self._slug: str | None = self.settings.company_slug

    async def aclose(self) -> None:
        await self._http.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        files: Any | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        async with self._semaphore:
            body, _headers = await self._request_with_retry(
                method, path, params=params, json=json, files=files, data=data
            )
            return body

    async def request_paginated(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        page: int = 0,
        page_size: int = DEFAULT_PAGE_SIZE,
        fetch_all: bool = False,
    ) -> dict[str, Any]:
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))
        base_params = dict(params or {})

        async def fetch(p: int) -> tuple[list[Any] | dict[str, Any], httpx.Headers]:
            async with self._semaphore:
                return await self._request_with_retry(
                    "GET", path, params={**base_params, "page": p, "pageSize": page_size}, json=None
                )

        body, headers = await fetch(page)
        if isinstance(body, dict) and body.get("error"):
            return body
        if not isinstance(body, list):
            return _error(500, f"Venta liste frå {path}, fekk {type(body).__name__}", body)

        total, page_count = _pagination_meta(headers)

        if not fetch_all:
            return {
                "data": body,
                "page": page,
                "page_size": page_size,
                "total": total,
                "page_count": page_count,
            }

        all_data: list[Any] = list(body)
        for p in range(page + 1, page_count):
            body, headers = await fetch(p)
            if isinstance(body, dict) and body.get("error"):
                return body
            if isinstance(body, list):
                all_data.extend(body)
        return {
            "data": all_data,
            "page": 0,
            "page_size": page_size,
            "total": total,
            "page_count": page_count,
            "fetched_all": True,
        }

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None,
        json: Any | None,
        files: Any | None = None,
        data: dict[str, Any] | None = None,
        attempt: int = 0,
    ) -> tuple[dict[str, Any] | list[Any], httpx.Headers]:
        try:
            response = await self._http.request(
                method, path, params=params, json=json, files=files, data=data
            )
        except httpx.HTTPError as exc:
            logger.warning("%s %s feil: %s", method, path, exc)
            return _error(0, f"HTTP-feil: {exc}", None), httpx.Headers()

        logger.debug("%s %s → %d", method, path, response.status_code)

        if response.status_code == 429 and attempt < 3:
            await asyncio.sleep(2**attempt)
            return await self._request_with_retry(
                method, path, params=params, json=json, files=files, data=data,
                attempt=attempt + 1,
            )

        if response.status_code >= 400:
            logger.warning("%s %s → %d", method, path, response.status_code)
            return (
                _error(
                    response.status_code,
                    _message_for_status(response.status_code),
                    _safe_json(response),
                ),
                response.headers,
            )

        if response.status_code == 204 or not response.content:
            return {}, response.headers
        return response.json(), response.headers

    async def get_company_slug(self) -> str | dict[str, Any]:
        if self._slug:
            return self._slug
        user = await self.request("GET", "/user/")
        if isinstance(user, dict) and user.get("error"):
            return user
        companies = await self.request("GET", "/companies/")
        if isinstance(companies, dict) and companies.get("error"):
            return companies
        if not companies:
            return _error(404, "Brukaren har ikkje tilgang til nokon selskap", None)
        slug = companies[0]["slug"] if isinstance(companies, list) else None
        if not slug:
            return _error(500, "Klarte ikkje å lese companySlug frå /companies/", companies)
        self._slug = slug
        return slug


def _pagination_meta(headers: httpx.Headers) -> tuple[int, int]:
    try:
        total = int(headers.get("fiken-api-result-count", "0"))
    except (TypeError, ValueError):
        total = 0
    try:
        page_count = int(headers.get("fiken-api-page-count", "0"))
    except (TypeError, ValueError):
        page_count = 0
    return total, page_count


def _message_for_status(status: int) -> str:
    if status == 401:
        return "Ugyldig eller manglande Fiken API-token"
    if status == 403:
        return "Ikkje tilgang til denne ressursen"
    if status == 404:
        return "Ressursen vart ikkje funnen"
    if status == 429:
        return "For mange førespurnader (rate limit) — gav opp etter 3 forsøk"
    return f"Fiken returnerte HTTP {status}"


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text or None


def _error(status_code: int, message: str, fiken_error: Any) -> dict[str, Any]:
    return {
        "error": True,
        "status_code": status_code,
        "message": message,
        "fiken_error": fiken_error,
    }
