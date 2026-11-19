import os
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
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
    # Stable ids. Aliases such as gemini-flash-latest can change between a rehearsal and the final.
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_fallback_model: str = "gemini-2.5-flash-lite"
    database_url: str = f"sqlite:///{DEFAULT_DB.as_posix()}"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    allowed_hosts: str = (
        "campusflow-api-598899050820.asia-south1.run.app,"
        "campusflow-api-stoxrroaqa-el.a.run.app,"
        "localhost,127.0.0.1,testserver"
    )
    environment: str = "development"
    demo_password: str = ""
    session_hours: int = 12
    allow_persona_header: bool = False
    # Used to hide fallback quiz answer positions from the public message id.
    app_secret: str = ""

    @model_validator(mode="after")
    def require_production_secrets(self) -> "Settings":
        if self.is_production:
            insecure = []
            if len(self.app_secret.strip()) < 32:
                insecure.append("APP_SECRET must be at least 32 characters")
            if not self.demo_password.strip():
                insecure.append("DEMO_PASSWORD must be set")
            if self.allow_persona_header:
                insecure.append("ALLOW_PERSONA_HEADER must be false")
            if insecure:
                raise ValueError(f"Production requires secure values for: {', '.join(insecure)}")
        return self

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def hosts(self) -> list[str]:
        return [item.strip() for item in self.allowed_hosts.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def ai_mode(self) -> str:
        return "gemini" if self.gemini_api_key.strip() else "deterministic-fallback"

    def assert_production(self) -> None:
        """Refuse to boot a production process that is still on demo defaults."""
        if not self.is_production:
            return
        problems: list[str] = []
        secret = self.app_secret.strip()
        if len(secret) < 32:
            problems.append("Set APP_SECRET to a random value of at least 32 characters")
        if not self.gemini_api_key.strip():
            problems.append("Set GEMINI_API_KEY")
        if not self.origins:
            problems.append("Set ALLOWED_ORIGINS")
        elif any("localhost" in origin or "127.0.0.1" in origin for origin in self.origins):
            problems.append("Set ALLOWED_ORIGINS to the deployed frontend origin")
        for name, model in (("GEMINI_MODEL", self.gemini_model), ("GEMINI_FALLBACK_MODEL", self.gemini_fallback_model)):
            if not model.strip() or "latest" in model.lower():
                problems.append(f"Pin {name} to a stable model id")
        if self.allow_persona_header:
            problems.append("Set ALLOW_PERSONA_HEADER=false")
        if "DEMO_PASSWORD" not in os.environ or not self.demo_password.strip():
            problems.append("Set DEMO_PASSWORD explicitly in the process environment")
        if problems:
            raise RuntimeError("Refusing to start in production: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
