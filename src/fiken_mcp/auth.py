"""OAuth 2.0 authorization-code flow for Fiken.

Fiken har berre *authorization code*-flyten (ingen client_credentials), så
tokenet må skaffast via ein eingongs nettlesar-godkjenning. `fiken-auth` (sjå
``main`` nedst) startar ein lokal callback-server, opnar nettlesaren, byter
koden mot access/refresh-token og lagrar dei på disk. Etterpå fornyar
``FikenClient`` access-tokenet automatisk med refresh-tokenet.
"""

from __future__ import annotations

import http.server
import json
import os
import secrets
import time
import urllib.parse
import webbrowser
from typing import Any

import httpx

from .config import Settings


class OAuthError(Exception):
    """Reist når autorisering eller token-forNYing feilar."""


# ── Token-lagring ────────────────────────────────────────────────────────────

def token_path(settings: Settings) -> str:
    return os.path.expanduser(settings.token_file)


def load_tokens(settings: Settings) -> dict[str, Any] | None:
    try:
        with open(token_path(settings), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return None


def save_tokens(settings: Settings, tokens: dict[str, Any]) -> None:
    path = token_path(settings)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Gjer eit token-svar frå Fiken om til vår lagra form."""
    if "access_token" not in payload:
        raise OAuthError(f"Token-svar utan access_token: {payload}")
    tokens: dict[str, Any] = {
        "access_token": payload["access_token"],
        "token_type": payload.get("token_type", "Bearer"),
    }
    if payload.get("refresh_token"):
        tokens["refresh_token"] = payload["refresh_token"]
    expires_in = payload.get("expires_in")
    if expires_in:
        # 60 s slingringsmon så vi fornyar litt før faktisk utløp
        tokens["expires_at"] = int(time.time()) + int(expires_in) - 60
    return tokens


# ── Token-endepunkt ──────────────────────────────────────────────────────────

def _token_data_authorization_code(settings: Settings, code: str) -> dict[str, str]:
    return {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.redirect_uri,
    }


async def refresh_tokens_async(
    settings: Settings, refresh_token: str, http: httpx.AsyncClient
) -> dict[str, Any]:
    """Forny access-tokenet. Kastar OAuthError ved feil."""
    resp = await http.post(
        f"{settings.auth_base_url}/token",
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        auth=(settings.client_id or "", settings.client_secret or ""),
        headers={"Accept": "application/json"},
    )
    if resp.status_code >= 400:
        raise OAuthError(f"Token-endepunkt HTTP {resp.status_code}: {resp.text}")
    return _normalize(resp.json())


def _exchange_code(settings: Settings, code: str) -> dict[str, Any]:
    resp = httpx.post(
        f"{settings.auth_base_url}/token",
        data=_token_data_authorization_code(settings, code),
        auth=(settings.client_id or "", settings.client_secret or ""),
        headers={"Accept": "application/json"},
        timeout=30.0,
    )
    if resp.status_code >= 400:
        raise OAuthError(f"Token-endepunkt HTTP {resp.status_code}: {resp.text}")
    return _normalize(resp.json())


# ── Nettlesar-flyt (eingongs) ────────────────────────────────────────────────

def _authorize_url(settings: Settings, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.client_id or "",
        "redirect_uri": settings.redirect_uri,
        "state": state,
    }
    if settings.scope:
        params["scope"] = settings.scope
    return f"{settings.auth_base_url}/authorize?" + urllib.parse.urlencode(params)


def _make_handler(callback_path: str, holder: dict[str, Any]):
    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != callback_path:
                self.send_response(404)
                self.end_headers()
                return
            qs = urllib.parse.parse_qs(parsed.query)
            holder["code"] = qs.get("code", [None])[0]
            holder["state"] = qs.get("state", [None])[0]
            holder["error"] = qs.get("error", [None])[0]
            ok = bool(holder["code"])
            msg = (
                "Fiken-autorisering fullført. Du kan lukke dette vindauget."
                if ok
                else f"Autorisering feila: {holder['error']}"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                f"<!doctype html><html lang='nn'><meta charset='utf-8'>"
                f"<body style='font-family:sans-serif'><h2>{msg}</h2></body></html>".encode()
            )

        def log_message(self, *args: Any) -> None:  # stille
            return

    return _Handler


def authorize(settings: Settings) -> dict[str, Any]:
    """Køyr heile nettlesar-flyten og lagre tokena. Returnerer tokena."""
    if not (settings.client_id and settings.client_secret):
        raise OAuthError("Manglar FIKEN_CLIENT_ID / FIKEN_CLIENT_SECRET i miljøet")

    parsed = urllib.parse.urlparse(settings.redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 80
    callback_path = parsed.path or "/"

    state = secrets.token_urlsafe(24)
    holder: dict[str, Any] = {}
    server = http.server.HTTPServer((host, port), _make_handler(callback_path, holder))

    url = _authorize_url(settings, state)
    print("Opnar nettlesaren for Fiken-autorisering. Om han ikkje opnar, lim inn:")
    print(f"\n  {url}\n")
    print(f"Ventar på redirect til {settings.redirect_uri} …")
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001 — nettlesar kan mangle i headless miljø
        pass

    try:
        while "code" not in holder and "error" not in holder:
            server.handle_request()
    finally:
        server.server_close()

    if holder.get("error"):
        raise OAuthError(f"Fiken avviste autorisering: {holder['error']}")
    if holder.get("state") != state:
        raise OAuthError("state stemmer ikkje — mogleg CSRF, avbryt")
    if not holder.get("code"):
        raise OAuthError("Fekk ingen autorisasjonskode frå Fiken")

    tokens = _exchange_code(settings, holder["code"])
    save_tokens(settings, tokens)
    return tokens


def main() -> None:
    settings = Settings()
    if settings.api_token:
        print(
            "FIKEN_API_TOKEN er sett → personleg token er i bruk, OAuth trengst ikkje.\n"
            "Fjern FIKEN_API_TOKEN frå .env om du vil bruke OAuth i staden."
        )
        return
    if not (settings.client_id and settings.client_secret):
        print("Manglar FIKEN_CLIENT_ID og/eller FIKEN_CLIENT_SECRET i .env.")
        raise SystemExit(1)
    try:
        authorize(settings)
    except OAuthError as exc:
        print(f"Feil: {exc}")
        raise SystemExit(1) from exc
    print(f"Ferdig ✔ Token lagra i {token_path(settings)}")


if __name__ == "__main__":
    main()
