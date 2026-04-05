from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NeuroSleepNet"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your_super_secret_key_here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "neurosleepnet"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/neurosleepnet"

    REDIS_URL: str = "redis://redis:6379/0"

    OPENAI_API_KEY: str = ""

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_PLAN_ID_MONTHLY: str = "plan_nsn_monthly"
    RAZORPAY_PLAN_ID_ANNUAL: str = "plan_nsn_annual"
    RAZORPAY_WEBHOOK_SECRET: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
