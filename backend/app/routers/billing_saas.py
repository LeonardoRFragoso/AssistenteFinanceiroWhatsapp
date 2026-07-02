from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.utils.dependencies import get_current_active_user, get_current_organization, get_current_user_role
from app.core.permissions import has_permission
from app.services.saas_billing_service import SaaSBillingService
from app.services.entitlements_service import EntitlementsService
from app.models.user import User
from app.models.organization import Organization, OrganizationRole
from app.core.logging import logger

router = APIRouter(prefix="/saas-billing", tags=["SaaS Billing"])


@router.get("/plans")
async def list_plans(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all available subscription plans."""
    service = SaaSBillingService(db)
    await service.seed_plans()
    plans = await service.list_plans(active_only=True)
    return [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "description": p.description,
            "price_monthly": str(p.price_monthly),
            "currency": p.currency,
            "max_charges_per_month": p.max_charges_per_month,
            "max_customers": p.max_customers,
            "max_team_members": p.max_team_members,
            "max_message_templates": p.max_message_templates,
            "max_recurring_tasks": p.max_recurring_tasks,
            "allow_advanced_analytics": p.allow_advanced_analytics,
            "allow_pdf_export": p.allow_pdf_export,
            "allow_ocr": p.allow_ocr,
            "allow_collection_rules": p.allow_collection_rules,
            "allow_whatsapp_intelligence": p.allow_whatsapp_intelligence,
        }
        for p in plans
    ]


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Get the current subscription for the organization."""
    service = SaaSBillingService(db)
    await service.ensure_free_subscription(org.id)
    return await service.get_subscription_summary(org.id)


@router.post("/subscription/change-plan")
async def change_plan(
    plan_code: str = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Change the organization's plan. Requires owner or admin role."""
    if not has_permission(role, "manage_settings"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner or admin can change the subscription plan",
        )
    service = SaaSBillingService(db)
    await service.ensure_free_subscription(org.id)
    try:
        sub = await service.change_plan(org.id, plan_code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {
        "id": sub.id,
        "plan_code": plan_code,
        "status": sub.status.value,
        "message": "Plan changed successfully (sandbox — no real payment processed)",
    }


@router.post("/subscription/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Cancel the organization's subscription. Requires owner or admin role."""
    if not has_permission(role, "manage_settings"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner or admin can cancel the subscription",
        )
    service = SaaSBillingService(db)
    try:
        sub = await service.cancel_subscription(org.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {
        "id": sub.id,
        "status": sub.status.value,
        "message": "Subscription cancelled. Downgraded to Free (sandbox — no real payment processed)",
    }


@router.post("/subscription/reactivate")
async def reactivate_subscription(
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Reactivate a cancelled subscription. Requires owner or admin role."""
    if not has_permission(role, "manage_settings"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner or admin can reactivate the subscription",
        )
    service = SaaSBillingService(db)
    try:
        sub = await service.reactivate_subscription(org.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {
        "id": sub.id,
        "status": sub.status.value,
        "message": "Subscription reactivated (sandbox — no real payment processed)",
    }


@router.get("/usage")
async def get_usage(
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Get usage counters for the current period."""
    service = SaaSBillingService(db)
    await service.ensure_free_subscription(org.id)
    usage = await service.get_usage(org.id)
    if not usage:
        return {
            "charges_created": 0,
            "customers_created": 0,
            "templates_created": 0,
            "recurring_tasks_created": 0,
            "ocr_documents_analyzed": 0,
            "pdf_exports_generated": 0,
            "whatsapp_messages_processed": 0,
            "collection_followups_generated": 0,
        }
    return {
        "charges_created": usage.charges_created,
        "customers_created": usage.customers_created,
        "templates_created": usage.templates_created,
        "recurring_tasks_created": usage.recurring_tasks_created,
        "ocr_documents_analyzed": usage.ocr_documents_analyzed,
        "pdf_exports_generated": usage.pdf_exports_generated,
        "whatsapp_messages_processed": usage.whatsapp_messages_processed,
        "collection_followups_generated": usage.collection_followups_generated,
    }


@router.get("/entitlements")
async def get_entitlements(
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Get the current entitlements for the organization."""
    service = SaaSBillingService(db)
    await service.ensure_free_subscription(org.id)
    return await service.get_entitlements(org.id)


@router.post("/fake/checkout")
async def fake_checkout(
    plan_code: str = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Simulate a checkout flow. Always succeeds. No real payment is processed."""
    if not has_permission(role, "manage_settings"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner or admin can checkout a plan",
        )
    service = SaaSBillingService(db)
    await service.ensure_free_subscription(org.id)
    try:
        sub = await service.fake_checkout(org.id, plan_code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {
        "id": sub.id,
        "plan_code": plan_code,
        "status": sub.status.value,
        "message": "Fake checkout completed (sandbox — no real payment processed)",
    }


@router.post("/fake/webhook")
async def fake_webhook(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Simulate a billing webhook. For testing purposes only."""
    service = SaaSBillingService(db)
    await service.ensure_free_subscription(org.id)
    logger.info(f"Fake billing webhook received for org {org.id}: {payload.get('event_type', 'unknown')}")
    return {"received": True, "message": "Fake webhook processed (sandbox)"}
