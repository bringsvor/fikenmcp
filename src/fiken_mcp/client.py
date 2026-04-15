import asyncio
from typing import Any

import httpx

from .config import Settings


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
    ) -> dict[str, Any] | list[Any]:
        async with self._semaphore:
            return await self._request_with_retry(method, path, params=params, json=json)

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None,
        json: Any | None,
        attempt: int = 0,
    ) -> dict[str, Any] | list[Any]:
        try:
            response = await self._http.request(method, path, params=params, json=json)
        except httpx.HTTPError as exc:
            return _error(0, f"HTTP-feil: {exc}", None)

        if response.status_code == 429 and attempt < 3:
            await asyncio.sleep(2**attempt)
            return await self._request_with_retry(
                method, path, params=params, json=json, attempt=attempt + 1
            )

        if response.status_code >= 400:
            return _error(
                response.status_code,
                _message_for_status(response.status_code),
                _safe_json(response),
            )

        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    async def get_company_slug(self) -> str | dict[str, Any]:
        if self._slug:
            return self._slug
        user = await self.request("GET", "/user/")
        if isinstance(user, dict) and user.get("error"):
            return user
        # Fiken returns a list of companies via /companies/ — pick the first if user has only one.
        # /user/ itself only returns user info, so we resolve via /companies/.
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
