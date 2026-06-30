from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from app.core.database import get_db
from app.schemas.payment import CheckoutRequest, CheckoutResponse, PaymentEventResponse
from app.schemas.plan import PlanResponse
from app.services.billing_service import BillingService
from app.repositories.plan_repository import PlanRepository
from app.repositories.payment_repository import PaymentRepository
from app.utils.dependencies import get_current_user
from app.models.user import User
from app.core.logging import logger

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/plans", response_model=list[PlanResponse])
async def get_plans(db: AsyncSession = Depends(get_db)):
    plan_repo = PlanRepository(db)
    plans = await plan_repo.get_all_active()
    return plans


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    checkout_data: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    billing_service = BillingService(db)
    
    checkout = await billing_service.create_checkout(
        user_id=current_user.id,
        user_email=current_user.email,
        plan_id=checkout_data.plan_id
    )
    
    if not checkout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create checkout"
        )
    
    return checkout


@router.get("/payments", response_model=list[PaymentEventResponse])
async def get_payment_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    payment_repo = PaymentRepository(db)
    payments = await payment_repo.get_by_user(current_user.id)
    return payments


@router.get("/usage")
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.plan_limit_service import PlanLimitService
    plan_service = PlanLimitService(db)
    return await plan_service.get_usage_stats(current_user.id)


@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    billing_service = BillingService(db)
    success = await billing_service.cancel_subscription(current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to cancel subscription"
        )
    
    return {"message": "Subscription cancelled successfully"}


@router.post("/webhook/mercado-pago")
async def mercado_pago_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        body = await request.json()
        headers = dict(request.headers)
        
        x_signature = headers.get("x-signature")
        x_request_id = headers.get("x-request-id")
        
        if not x_signature or not x_request_id:
            logger.warning("Webhook without signature headers - rejecting")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing signature headers"
            )
        
        from app.integrations.mercado_pago import MercadoPagoService
        mp_service = MercadoPagoService()

        url = str(request.url)
        is_valid = mp_service.validate_webhook_signature_from_url(
            url=url,
            x_signature=x_signature,
            x_request_id=x_request_id
        )

        if not is_valid:
            logger.warning(f"Invalid webhook signature from Mercado Pago - rejecting")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

        from app.utils.log_sanitizer import sanitize_webhook_data
        logger.info(f"Received valid Mercado Pago webhook: {sanitize_webhook_data(body)}")
        
        billing_service = BillingService(db)
        success = await billing_service.process_payment_webhook(body)
        
        if success:
            return {"status": "processed"}
        else:
            return {"status": "ignored"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Mercado Pago webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook"
        )
