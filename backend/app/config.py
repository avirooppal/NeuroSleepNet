import os
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NeuroSleepNet"
    VERSION: str = "0.2.0"

    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your_super_secret_key_here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALLOW_ANONYMOUS_ACCESS: bool = False

    # ── Fix 5: CORS origins — env-configurable, never wildcard ───────────────
    # Set ALLOWED_ORIGINS in .env as a comma-separated list:
    #   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── Database ──────────────────────────────────────────────────────────────
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "neurosleepnet"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/neurosleepnet"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── Embedding sidecar ─────────────────────────────────────────────────────
    EMBED_SERVICE_URL: str = "http://nsn-embed:8001"

    # ── Fix 13: Encryption key — REQUIRED in production, no default ──────────
    # Generate with: python -c "import secrets; print(secrets.token_hex(16))"
    # Set in .env: NSN_ENCRYPTION_MASTER_KEY=<your-32-char-key>
    NSN_ENCRYPTION_MASTER_KEY: str = ""
    NSN_ENCRYPTION_KEY: str = ""   # legacy alias — kept for migration
    NSN_PII_DETECTION_ENABLED: bool = True

    # ── GitHub OAuth ──────────────────────────────────────────────────────────
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Optional integrations ─────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_PLAN_ID_MONTHLY: str = "plan_nsn_monthly"
    RAZORPAY_PLAN_ID_ANNUAL: str = "plan_nsn_annual"
    RAZORPAY_WEBHOOK_SECRET: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    def validate_encryption_key(self) -> None:
        """
        Called at startup. Refuses to run with a known-insecure or empty key.
        Fix 13: prevents deployers from shipping with the default placeholder.
        """
        _FORBIDDEN = {
            "",
            "changeme-in-production-32chars!!",
            "changeme",
            "secret",
            "your_key_here",
        }
        key = self.NSN_ENCRYPTION_MASTER_KEY or self.NSN_ENCRYPTION_KEY
        if key in _FORBIDDEN or len(key) < 32:
            raise RuntimeError(
                "NSN_ENCRYPTION_MASTER_KEY is insecure or not set. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(16))\"\n"
                "Set this in your .env file."
            )


settings = Settings()
