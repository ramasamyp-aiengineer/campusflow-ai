from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "campusflow.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    gemini_fallback_model: str = "gemini-flash-lite-latest"
    database_url: str = f"sqlite:///{DEFAULT_DB.as_posix()}"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    environment: str = "development"
    demo_password: str = "CampusFlow@2026"
    session_hours: int = 12
    allow_persona_header: bool = False

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def ai_mode(self) -> str:
        return "gemini" if self.gemini_api_key.strip() else "deterministic-fallback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
