from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NeuroSleepNet"
    NSN_PII_DETECTION_ENABLED: bool = True
    NSN_ENCRYPTION_KEY: str = "J1d2Y1xM2fO9A2qP0bW3cE7rK5mN8vT6" # Must be 32 bytes for AES-256 in prod
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your_super_secret_key_here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALLOW_ANONYMOUS_ACCESS: bool = False

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "neurosleepnet"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/neurosleepnet"

    REDIS_URL: str = "redis://redis:6379/0"
    EMBED_SERVICE_URL: str = "http://nsn-embed:8001"

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    # Where to send the user after successful login (frontend)
    FRONTEND_URL: str = "http://localhost:3000"

    OPENAI_API_KEY: str = ""

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_PLAN_ID_MONTHLY: str = "plan_nsn_monthly"
    RAZORPAY_PLAN_ID_ANNUAL: str = "plan_nsn_annual"
    RAZORPAY_WEBHOOK_SECRET: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
