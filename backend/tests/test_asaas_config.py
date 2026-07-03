"""
Tests for Asaas configuration and provider factory integration.
Sprint 15 — Asaas sandbox provider.
"""
import pytest
from app.core.config import Settings


def test_asaas_config_defaults():
    """Asaas config vars should default to disabled/sandbox."""
    s = Settings(
        DATABASE_URL="sqlite:///test.db",
        SECRET_KEY="test-secret",
    )
    assert s.ASAAS_ENVIRONMENT == "sandbox"
    assert s.ASAAS_API_BASE_URL == "https://sandbox.asaas.com/api/v3"
    assert s.ASAAS_API_KEY is None
    assert s.ASAAS_WEBHOOK_TOKEN is None
    assert s.ENABLE_ASAAS_CHARGE_PROVIDER is False


def test_asaas_config_can_be_enabled():
    """Asaas config can be set via env."""
    s = Settings(
        DATABASE_URL="sqlite:///test.db",
        SECRET_KEY="test-secret",
        ENABLE_ASAAS_CHARGE_PROVIDER=True,
        ASAAS_API_KEY="test-key-123",
        ASAAS_WEBHOOK_TOKEN="test-webhook-token-32chars-min!!!",
    )
    assert s.ENABLE_ASAAS_CHARGE_PROVIDER is True
    assert s.ASAAS_API_KEY == "test-key-123"
    assert s.ASAAS_WEBHOOK_TOKEN == "test-webhook-token-32chars-min!!!"


def test_provider_factory_defaults_to_fake():
    """Provider factory should default to fake when no provider is set."""
    import app.providers.provider_factory as factory
    factory._PAYMENT_PROVIDER = None
    provider = factory.get_payment_provider("fake")
    assert provider.name == "fake"


def test_provider_factory_asaas_without_enable_raises():
    """Provider factory should raise if Asaas is requested but not enabled."""
    import app.providers.provider_factory as factory
    factory._PAYMENT_PROVIDER = None
    with pytest.raises(RuntimeError, match="not enabled"):
        factory.get_payment_provider("asaas")


def test_provider_factory_asaas_with_demo_mode_raises():
    """Provider factory should raise if Asaas is requested in demo mode."""
    import app.providers.provider_factory as factory
    from app.core.config import settings
    factory._PAYMENT_PROVIDER = None
    old_demo = settings.ENABLE_DEMO_MODE
    old_enable = settings.ENABLE_ASAAS_CHARGE_PROVIDER
    try:
        settings.ENABLE_DEMO_MODE = True
        settings.ENABLE_ASAAS_CHARGE_PROVIDER = True
        with pytest.raises(RuntimeError, match="Demo mode"):
            factory.get_payment_provider("asaas")
    finally:
        settings.ENABLE_DEMO_MODE = old_demo
        settings.ENABLE_ASAAS_CHARGE_PROVIDER = old_enable


def test_provider_factory_asaas_without_api_key_raises():
    """Provider factory should raise if Asaas is enabled but API key is missing."""
    import app.providers.provider_factory as factory
    from app.core.config import settings
    factory._PAYMENT_PROVIDER = None
    old_demo = settings.ENABLE_DEMO_MODE
    old_enable = settings.ENABLE_ASAAS_CHARGE_PROVIDER
    old_key = settings.ASAAS_API_KEY
    try:
        settings.ENABLE_DEMO_MODE = False
        settings.ENABLE_ASAAS_CHARGE_PROVIDER = True
        settings.ASAAS_API_KEY = None
        with pytest.raises(RuntimeError, match="ASAAS_API_KEY"):
            factory.get_payment_provider("asaas")
    finally:
        settings.ENABLE_DEMO_MODE = old_demo
        settings.ENABLE_ASAAS_CHARGE_PROVIDER = old_enable
        settings.ASAAS_API_KEY = old_key


def test_provider_factory_unknown_in_production_raises():
    """Provider factory should raise for unknown provider in production."""
    import app.providers.provider_factory as factory
    from app.core.config import settings
    factory._PAYMENT_PROVIDER = None
    old_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        with pytest.raises(RuntimeError, match="Unknown payment provider"):
            factory.get_payment_provider("nonexistent")
    finally:
        settings.ENVIRONMENT = old_env
