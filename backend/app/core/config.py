"""Uygulama ayarları. Tüm secret değerler ortam değişkenlerinden okunur;
hiçbir secret kod içine veya varsayılan değer olarak yazılmaz."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    app_secret_key: str
    access_token_expire_minutes: int = 60 * 12  # 12 saat

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    anthropic_api_key: str | None = None
    ai_model: str = "claude-sonnet-5-5"

    telegram_bot_token: str | None = None
    telegram_allowed_user_ids: str = ""

    # Varsayılan yalnızca yerel (docker'sız) geliştirme için: Vite dev
    # server'ın 5173 portu. docker-compose'daki dockerized frontend
    # farklı bir portta (8081) servis edildiği için backend servisinde
    # bu değişken override edilir (bkz. docker-compose.yml).
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def telegram_allowed_ids(self) -> set[int]:
        return {
            int(v) for v in self.telegram_allowed_user_ids.split(",") if v.strip()
        }

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [v.strip() for v in self.cors_allowed_origins.split(",") if v.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
