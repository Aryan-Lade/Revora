from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    environment: str = "development"
    demo_mode: bool = True
    database_url: str = "sqlite:///./revora.db"
    frontend_url: str = "http://localhost:5173"
    port: int = 8000

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    ai_api_key: str = ""
    ai_model: str = "claude-opus-5"

    voice_provider: str = "demo"
    voice_api_key: str = ""
    email_provider: str = "demo"
    email_api_key: str = ""

    quiet_hours_start: int = 22
    quiet_hours_end: int = 8
    max_retry_attempts: int = 3
    max_automated_amount: float = 10000.0
    min_ai_confidence: float = 0.70
    recovery_window_hours: int = 72
    max_contacts_per_window: int = 3
    max_voice_per_day: int = 1
    max_email_per_day: int = 1

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def live_razorpay(self) -> bool:
        return not self.demo_mode and bool(self.razorpay_key_id and self.razorpay_key_secret)

    @property
    def live_ai(self) -> bool:
        return not self.demo_mode and bool(self.ai_api_key)

    @property
    def allowed_origins(self) -> list[str]:
        origins = {self.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"}
        return sorted(o for o in origins if o)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
