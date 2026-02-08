from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    app_name: str = 'Smart Vault API'
    environment: str = 'development'
    DEV_AUTH_BYPASS: bool = False
    DATABASE_URL: str = 'postgresql+psycopg://postgres:postgres@localhost:5432/smartvault'
    REDIS_URL: str = 'redis://redis:6379/0'
    
    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Email / SMTP
    EMAIL_BACKEND: str | None = None  # "dev" or "smtp"
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_FROM_NAME: str | None = None

    # OTP + ticket
    OTP_TTL_SECONDS: int = 600          # 10 min
    SIGNUP_TICKET_TTL_SECONDS: int = 300 # 5 min
    
    # Rate Limiting
    RATE_LIMIT_OTP_REQ_PER_MIN: int = 3
    RATE_LIMIT_LOGIN_REQ_PER_MIN: int = 5

    # Internal surfaces
    INTERNAL_OPS_TOKEN_HASH: str | None = None
    INTERNAL_OPS_TOKEN_ID: str | None = None
    INTERNAL_OPS_RATE_LIMIT_PER_MIN: int = 60

    ADMIN_SHARED_TOKEN_HASH: str | None = None
    ADMIN_TOKEN_ID: str | None = None
    ADMIN_JWT_SECRET: str | None = None
    ADMIN_JWT_ALGORITHM: str = "HS256"
    INTERNAL_ADMIN_RATE_LIMIT_PER_MIN: int = 20
    
    @property
    def resolved_email_backend(self) -> str:
        """Choose email backend based on explicit setting, environment, and SMTP availability."""
        explicit = self.EMAIL_BACKEND.lower() if self.EMAIL_BACKEND else None
        if explicit:
            return explicit

        env = (self.environment or '').lower()
        if env == 'development' or not self.SMTP_HOST:
            return 'dev'
        return 'smtp'


settings = Settings()
