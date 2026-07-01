from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: Optional[str] = None
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    TWILIO_VALIDATE_SIGNATURE: bool = True

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    MERCADO_PAGO_ACCESS_TOKEN: Optional[str] = None
    MERCADO_PAGO_PUBLIC_KEY: Optional[str] = None
    MERCADO_PAGO_WEBHOOK_SECRET: Optional[str] = None

    PAYFLOW_PAYMENT_PROVIDER: str = "fake"
    
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    ENABLE_WORKER: bool = True
    ENABLE_CHARGE_REMINDER_WORKER: bool = False
    CHARGE_REMINDER_INTERVAL_MINUTES: int = 60
    
    # Admin access (comma-separated emails)
    ADMIN_EMAILS: str = ""
    
    # Demo mode (disabled by default)
    ENABLE_DEMO_MODE: bool = False
    DEMO_USER_EMAIL: str = "demo@payflow.ai"
    DEMO_USER_PASSWORD: str = "PayFlowDemo123"
    
    # Sentry (optional, disabled by default)
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0
    
    # User rate limiting (authenticated endpoints)
    USER_RATE_LIMIT_ENABLED: bool = True
    USER_RATE_LIMIT_CHARGES_PER_MINUTE: int = 20
    USER_RATE_LIMIT_EXPORTS_PER_MINUTE: int = 10
    USER_RATE_LIMIT_DEMO_RESET_PER_HOUR: int = 5
    
    # Webhook rate limiting
    WEBHOOK_RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
