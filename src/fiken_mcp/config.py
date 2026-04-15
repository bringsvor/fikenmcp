from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FIKEN_", extra="ignore")

    api_token: str
    company_slug: str | None = None
    base_url: str = "https://api.fiken.no/api/v2"
