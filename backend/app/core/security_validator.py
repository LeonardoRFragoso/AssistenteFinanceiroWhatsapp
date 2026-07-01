"""
Security validator for critical configuration at startup
"""
import sys
from app.core.config import settings
from app.core.logging import logger


def validate_secret_key():
    """
    Validates that SECRET_KEY is strong enough for production use.
    Raises SystemExit if key is weak or default.
    """
    secret_key = settings.SECRET_KEY
    
    # Check if using default/example key
    weak_keys = [
        "your-secret-key-change-in-production",
        "changeme",
        "secret",
        "secretkey",
        "your-secret-key",
        "dev-secret-key"
    ]
    
    if secret_key.lower() in weak_keys:
        logger.critical("🚨 CRITICAL SECURITY ERROR: SECRET_KEY is using a default/weak value!")
        logger.critical("Generate a strong key with: python scripts/generate_secret_key.py")
        logger.critical("Or use: python -c \"import secrets; print(secrets.token_urlsafe(64))\"")
        sys.exit(1)
    
    # Check minimum length (256 bits = 64 hex chars, but we accept 32+ for flexibility)
    if len(secret_key) < 32:
        logger.critical(f"🚨 CRITICAL SECURITY ERROR: SECRET_KEY is too short ({len(secret_key)} chars)")
        logger.critical("Minimum required: 32 characters")
        logger.critical("Recommended: 64+ characters for maximum security")
        logger.critical("Generate with: python scripts/generate_secret_key.py")
        sys.exit(1)
    
    # Warn if not using recommended length
    if len(secret_key) < 64:
        logger.warning(f"⚠️  SECRET_KEY length is {len(secret_key)} chars. Recommended: 64+ chars for maximum security")
    
    logger.info("✅ SECRET_KEY validation passed")


def validate_demo_mode():
    """
    Validates that demo mode is not used in production and that demo mode
    always uses the fake payment provider.
    Raises SystemExit if configuration is unsafe.
    """
    if not settings.ENABLE_DEMO_MODE:
        return

    if settings.ENVIRONMENT == "production":
        logger.critical("🚨 CRITICAL SECURITY ERROR: ENABLE_DEMO_MODE cannot be true in production.")
        logger.critical("Set ENABLE_DEMO_MODE=false or change ENVIRONMENT to development/demo.")
        sys.exit(1)

    if settings.PAYFLOW_PAYMENT_PROVIDER.lower().strip() != "fake":
        logger.critical("🚨 CRITICAL SECURITY ERROR: Demo mode requires PAYFLOW_PAYMENT_PROVIDER=fake.")
        logger.critical(f"Current provider: '{settings.PAYFLOW_PAYMENT_PROVIDER}'. Set PAYFLOW_PAYMENT_PROVIDER=fake.")
        sys.exit(1)

    logger.info("✅ Demo mode validation passed (fake provider, non-production)")


def validate_production_config():
    """
    Validates critical production configuration.
    """
    # Always validate demo mode safety (applies to all environments)
    validate_demo_mode()

    # Only validate in production environment
    if settings.ENVIRONMENT != "production":
        logger.info("Skipping production validation in non-production environment")
        return
    
    validate_secret_key()
    
    # Validate Mercado Pago webhook secret exists
    if not settings.MERCADO_PAGO_WEBHOOK_SECRET:
        logger.warning("⚠️  MERCADO_PAGO_WEBHOOK_SECRET not set - webhook validation will fail")

    # Validate Twilio webhook signature validation is enabled in production
    if not settings.TWILIO_VALIDATE_SIGNATURE:
        logger.critical("🚨 CRITICAL SECURITY ERROR: TWILIO_VALIDATE_SIGNATURE is disabled in production!")
        logger.critical("WhatsApp webhook signature validation must be enabled in production.")
        sys.exit(1)

    # Validate JWT expiration is reasonable
    if settings.ACCESS_TOKEN_EXPIRE_MINUTES > 1440:  # 24 hours
        logger.warning(f"⚠️  ACCESS_TOKEN_EXPIRE_MINUTES is {settings.ACCESS_TOKEN_EXPIRE_MINUTES} - consider shorter expiration for security")
    
    logger.info("✅ Production configuration validation completed")
