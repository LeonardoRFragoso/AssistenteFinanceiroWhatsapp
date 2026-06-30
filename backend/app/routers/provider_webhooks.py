from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from app.core.database import get_db
from app.core.config import settings
from app.core.logging import logger
from app.services.charge_service import ChargeService
from app.integrations.mercado_pago import MercadoPagoService
from app.utils.log_sanitizer import sanitize_webhook_data

router = APIRouter(prefix="/provider-webhooks", tags=["Provider Webhooks"])


@router.post("/fake")
async def fake_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Receive fake/sandbox provider events."""
    try:
        payload = await request.json()
        logger.info(f"Received fake provider webhook: {sanitize_webhook_data(payload)}")

        service = ChargeService(db)
        charge = await service.process_webhook_payload("fake", payload)

        if charge:
            return {"status": "processed", "charge_id": charge.id}
        return {"status": "ignored"}

    except Exception as e:
        logger.error(f"Error processing fake webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook"
        )


@router.post("/fake/pay/{provider_charge_id}")
async def fake_simulate_payment(
    provider_charge_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Sandbox helper to simulate a payment for a fake charge.

    Only available in development/testing environments.
    """
    if settings.ENVIRONMENT.lower() not in ("development", "testing", "dev"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulation endpoint is only available in development/testing"
        )

    try:
        from app.providers.fake_provider import FakePaymentProvider
        provider = FakePaymentProvider()
        service = ChargeService(db)
        charge = await service.charge_repo.get_by_provider_charge_id(provider_charge_id)
        if not charge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Charge not found"
            )

        payload = provider.build_payment_simulation_payload(
            provider_charge_id=provider_charge_id,
            amount=charge.amount
        )
        updated_charge = await service.process_webhook_payload("fake", payload)
        return {
            "status": "simulated",
            "charge_id": updated_charge.id if updated_charge else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error simulating fake payment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error simulating payment"
        )


@router.post("/mercado-pago")
async def mercado_pago_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Receive Mercado Pago payment notifications for PayFlow charges.

    This endpoint is separate from the billing subscription webhook to keep
    charge flows isolated from subscription flows.
    """
    try:
        body = await request.json()
        headers = dict(request.headers)

        x_signature = headers.get("x-signature")
        x_request_id = headers.get("x-request-id")

        if not x_signature or not x_request_id:
            logger.warning("Mercado Pago provider webhook without signature headers - rejecting")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing signature headers"
            )

        mp_service = MercadoPagoService()
        url = str(request.url)
        is_valid = mp_service.validate_webhook_signature_from_url(
            url=url,
            x_signature=x_signature,
            x_request_id=x_request_id
        )

        if not is_valid:
            logger.warning("Invalid Mercado Pago provider webhook signature - rejecting")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

        logger.info(f"Received valid Mercado Pago provider webhook: {sanitize_webhook_data(body)}")

        service = ChargeService(db)
        charge = await service.process_webhook_payload("mercado_pago", body)

        if charge:
            return {"status": "processed", "charge_id": charge.id}
        return {"status": "ignored"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Mercado Pago provider webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook"
        )
