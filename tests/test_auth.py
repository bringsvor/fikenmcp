import time

import httpx
import respx

from fiken_mcp import auth
from fiken_mcp.client import FikenClient
from fiken_mcp.config import Settings

BASE = "https://api.fiken.no/api/v2"
OAUTH = "https://fiken.no/oauth"
SLUG = "test-company"


def _oauth_settings(tmp_path, **over):
    kwargs = dict(
        api_token=None,
        client_id="cid",
        client_secret="csecret",
        company_slug=SLUG,
        base_url=BASE,
        token_file=str(tmp_path / "tokens.json"),
    )
    kwargs.update(over)
    # _env_file=None → ikkje les den ekte .env (elles lek client_id/token inn)
    return Settings(_env_file=None, **kwargs)


# ── Settings / val av flyt ───────────────────────────────────────────────────

def test_use_oauth_true_when_client_creds(tmp_path):
    assert _oauth_settings(tmp_path).use_oauth is True


def test_use_oauth_false_when_api_token_present(tmp_path):
    s = _oauth_settings(tmp_path, api_token="tok")
    assert s.use_oauth is False


# ── Token-lagring ────────────────────────────────────────────────────────────

def test_save_and_load_roundtrip(tmp_path):
    s = _oauth_settings(tmp_path)
    tokens = {"access_token": "a", "refresh_token": "r", "expires_at": 123}
    auth.save_tokens(s, tokens)
    assert auth.load_tokens(s) == tokens


def test_load_missing_returns_none(tmp_path):
    assert auth.load_tokens(_oauth_settings(tmp_path)) is None


def test_normalize_sets_expires_at():
    out = auth._normalize({"access_token": "a", "refresh_token": "r", "expires_in": 3600})
    assert out["access_token"] == "a"
    assert out["expires_at"] > time.time()


# ── Klient: personleg token ──────────────────────────────────────────────────

async def test_personal_token_header():
    s = Settings(_env_file=None, api_token="pat-123", company_slug=SLUG, base_url=BASE)
    c = FikenClient(s)
    hdr = await c._auth_header()
    assert hdr == {"Authorization": "Bearer pat-123"}
    await c.aclose()


async def test_no_auth_configured_returns_error():
    s = Settings(_env_file=None, company_slug=SLUG, base_url=BASE)
    c = FikenClient(s)
    hdr = await c._auth_header()
    assert hdr["error"] is True
    assert hdr["status_code"] == 401
    await c.aclose()


# ── Klient: OAuth ────────────────────────────────────────────────────────────

async def test_oauth_not_authorized_yet(tmp_path):
    c = FikenClient(_oauth_settings(tmp_path))
    hdr = await c._auth_header()
    assert hdr["error"] is True
    assert "autoriser" in hdr["message"]
    await c.aclose()


async def test_oauth_uses_stored_token(tmp_path):
    s = _oauth_settings(tmp_path)
    auth.save_tokens(s, {"access_token": "live", "refresh_token": "r"})
    c = FikenClient(s)
    hdr = await c._auth_header()
    assert hdr == {"Authorization": "Bearer live"}
    await c.aclose()


@respx.mock
async def test_oauth_proactive_refresh_on_expiry(tmp_path):
    s = _oauth_settings(tmp_path)
    auth.save_tokens(s, {"access_token": "old", "refresh_token": "r0", "expires_at": 1})
    respx.post(f"{OAUTH}/token").respond(
        200, json={"access_token": "new", "refresh_token": "r1", "expires_in": 3600}
    )
    c = FikenClient(s)
    hdr = await c._auth_header()
    assert hdr == {"Authorization": "Bearer new"}
    # ny token er persistert
    assert auth.load_tokens(s)["access_token"] == "new"
    await c.aclose()


@respx.mock
async def test_oauth_refresh_keeps_old_refresh_token(tmp_path):
    s = _oauth_settings(tmp_path)
    auth.save_tokens(s, {"access_token": "old", "refresh_token": "keepme", "expires_at": 1})
    respx.post(f"{OAUTH}/token").respond(200, json={"access_token": "new", "expires_in": 3600})
    c = FikenClient(s)
    await c._auth_header()
    assert auth.load_tokens(s)["refresh_token"] == "keepme"
    await c.aclose()


@respx.mock
async def test_oauth_reactive_refresh_on_401(tmp_path):
    s = _oauth_settings(tmp_path)
    auth.save_tokens(s, {"access_token": "stale", "refresh_token": "r0"})
    api = respx.get(f"{BASE}/companies/{SLUG}/contacts/1")
    api.side_effect = [
        httpx.Response(401, json={"message": "expired"}),
        httpx.Response(200, json={"contactId": 1, "name": "Acme"}),
    ]
    respx.post(f"{OAUTH}/token").respond(
        200, json={"access_token": "fresh", "refresh_token": "r1", "expires_in": 3600}
    )
    c = FikenClient(s)
    result = await c.request("GET", f"/companies/{SLUG}/contacts/1")
    assert result == {"contactId": 1, "name": "Acme"}
    assert api.call_count == 2
    await c.aclose()


@respx.mock
async def test_oauth_401_without_refresh_token_surfaces_error(tmp_path):
    s = _oauth_settings(tmp_path)
    auth.save_tokens(s, {"access_token": "stale"})  # ingen refresh_token
    respx.get(f"{BASE}/companies/{SLUG}/contacts/1").respond(401, json={"message": "expired"})
    c = FikenClient(s)
    result = await c.request("GET", f"/companies/{SLUG}/contacts/1")
    assert result["error"] is True
    assert result["status_code"] == 401
    await c.aclose()
