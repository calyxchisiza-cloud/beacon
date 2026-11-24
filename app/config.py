from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+pysqlite:///./beacon.db"
    redis_url: str = ""
    jwt_secret: str = "change-me"
    jwt_ttl_seconds: int = 12 * 60 * 60
    sentry_dsn: str = ""
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
