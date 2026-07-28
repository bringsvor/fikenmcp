from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FIKEN_", extra="ignore")

    # Auth — enten personleg token ELLER OAuth (client_id + client_secret).
    api_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None

    # OAuth-oppsett
    redirect_uri: str = "http://localhost:8473/callback"
    scope: str = ""  # Fiken-appen avgjer scope; tom = ikkje send scope-param
    token_file: str = "~/.config/fiken-mcp/tokens.json"
    auth_base_url: str = "https://fiken.no/oauth"

    company_slug: str | None = None
    base_url: str = "https://api.fiken.no/api/v2"

    @property
    def use_oauth(self) -> bool:
        """OAuth når client_id/secret finst og ingen personleg token er sett."""
        return bool(self.client_id and self.client_secret) and not self.api_token
