"""
Tests for Open Finance WhatsApp intents — Sprint 16.

Tests the WhatsApp intent handlers for fake financial data reading.
Verifies demo data indication and safe messaging.
"""
import pytest
from app.services.open_finance_service import OpenFinanceService
from app.services.ai_service import AIService


@pytest.mark.asyncio
async def test_of_balance_summary_no_accounts(db_session, sample_organization, sample_user):
    """Test balance summary when no accounts are connected."""
    from app.routers.webhook import handle_of_balance_summary
    ai_service = AIService()
    result = await handle_of_balance_summary(sample_user.id, {}, db_session, ai_service, "")
    assert "demonstração" in result.lower() or "demo" in result.lower()


@pytest.mark.asyncio
async def test_of_balance_summary_with_accounts(db_session, sample_organization, sample_user):
    """Test balance summary with connected accounts."""
    from app.routers.webhook import handle_of_balance_summary
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)
    await service.sync_fake_accounts(sample_organization.id, sample_user.id, consent.id)

    ai_service = AIService()
    result = await handle_of_balance_summary(sample_user.id, {}, db_session, ai_service, "")
    assert "Open Finance" in result
    assert "demonstração" in result.lower() or "demo" in result.lower()
    assert "R$" in result


@pytest.mark.asyncio
async def test_of_recent_transactions_no_data(db_session, sample_organization, sample_user):
    """Test recent transactions when no data exists."""
    from app.routers.webhook import handle_of_recent_transactions
    ai_service = AIService()
    result = await handle_of_recent_transactions(sample_user.id, {}, db_session, ai_service, "")
    assert "demonstração" in result.lower() or "demo" in result.lower()


@pytest.mark.asyncio
async def test_of_recent_transactions_with_data(db_session, sample_organization, sample_user):
    """Test recent transactions with synced data."""
    from app.routers.webhook import handle_of_recent_transactions
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)
    await service.sync_fake_accounts(sample_organization.id, sample_user.id, consent.id)
    await service.sync_fake_transactions(sample_organization.id, sample_user.id)

    ai_service = AIService()
    result = await handle_of_recent_transactions(sample_user.id, {}, db_session, ai_service, "")
    assert "transações" in result.lower() or "transacao" in result.lower()
    assert "demonstração" in result.lower() or "demo" in result.lower()


@pytest.mark.asyncio
async def test_of_monthly_summary(db_session, sample_organization, sample_user):
    """Test monthly summary intent."""
    from app.routers.webhook import handle_of_monthly_summary
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)
    await service.sync_fake_accounts(sample_organization.id, sample_user.id, consent.id)
    await service.sync_fake_transactions(sample_organization.id, sample_user.id)

    ai_service = AIService()
    result = await handle_of_monthly_summary(sample_user.id, {}, db_session, ai_service, "")
    assert "resumo" in result.lower()
    assert "demonstração" in result.lower() or "demo" in result.lower()
    assert "R$" in result


@pytest.mark.asyncio
async def test_of_monthly_summary_no_data(db_session, sample_organization, sample_user):
    """Test monthly summary with no data."""
    from app.routers.webhook import handle_of_monthly_summary
    ai_service = AIService()
    result = await handle_of_monthly_summary(sample_user.id, {}, db_session, ai_service, "")
    assert "R$" in result
    assert "demonstração" in result.lower() or "demo" in result.lower()


@pytest.mark.asyncio
async def test_of_category_summary_no_data(db_session, sample_organization, sample_user):
    """Test category summary with no data."""
    from app.routers.webhook import handle_of_category_summary
    ai_service = AIService()
    result = await handle_of_category_summary(sample_user.id, {}, db_session, ai_service, "")
    assert "demonstração" in result.lower() or "demo" in result.lower()


@pytest.mark.asyncio
async def test_of_category_summary_with_data(db_session, sample_organization, sample_user):
    """Test category summary with synced data."""
    from app.routers.webhook import handle_of_category_summary
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)
    await service.sync_fake_accounts(sample_organization.id, sample_user.id, consent.id)
    await service.sync_fake_transactions(sample_organization.id, sample_user.id)

    ai_service = AIService()
    result = await handle_of_category_summary(sample_user.id, {}, db_session, ai_service, "")
    assert "Categorias" in result or "categorias" in result.lower()
    assert "demonstração" in result.lower() or "demo" in result.lower()


@pytest.mark.asyncio
async def test_of_search_transactions_no_term(db_session, sample_organization, sample_user):
    """Test search transactions without a search term."""
    from app.routers.webhook import handle_of_search_transactions
    ai_service = AIService()
    result = await handle_of_search_transactions(sample_user.id, {}, db_session, ai_service, "")
    assert "buscar" in result.lower() or "termo" in result.lower()


@pytest.mark.asyncio
async def test_of_search_transactions_with_term(db_session, sample_organization, sample_user):
    """Test search transactions with a search term."""
    from app.routers.webhook import handle_of_search_transactions
    service = OpenFinanceService(db_session)
    consent = await service.create_fake_consent(sample_organization.id, sample_user.id)
    await service.sync_fake_accounts(sample_organization.id, sample_user.id, consent.id)
    await service.sync_fake_transactions(sample_organization.id, sample_user.id)

    ai_service = AIService()
    result = await handle_of_search_transactions(
        sample_user.id, {"search_term": "supermercado"}, db_session, ai_service, ""
    )
    assert "demonstração" in result.lower() or "demo" in result.lower()


@pytest.mark.asyncio
async def test_of_all_intents_mention_demo(db_session, sample_organization, sample_user):
    """Test that all Open Finance WhatsApp intents mention demo/demonstração."""
    from app.routers.webhook import (
        handle_of_balance_summary,
        handle_of_recent_transactions,
        handle_of_monthly_summary,
        handle_of_category_summary,
    )
    ai_service = AIService()
    intents = [
        handle_of_balance_summary,
        handle_of_recent_transactions,
        handle_of_monthly_summary,
        handle_of_category_summary,
    ]

    for intent_fn in intents:
        result = await intent_fn(sample_user.id, {}, db_session, ai_service, "")
        assert "demonstração" in result.lower() or "demo" in result.lower(), \
            f"Intent {intent_fn.__name__} does not mention demo/demonstração"
