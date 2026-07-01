from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.utils.dependencies import get_current_active_user
from app.utils.user_rate_limiter import demo_reset_limiter
from app.core.audit_logger import log_demo_reset
from app.models.user import User

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.post("/reset")
async def reset_demo_data(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset demo user data. Only available in development or demo mode, never in production."""
    await demo_reset_limiter.check(current_user.id, "demo_reset")

    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=403,
            detail="Demo reset is not available in production"
        )

    if not settings.ENABLE_DEMO_MODE:
        raise HTTPException(
            status_code=404,
            detail="Demo mode is not enabled"
        )

    # Defense in depth: verify provider is fake
    if settings.PAYFLOW_PAYMENT_PROVIDER.lower().strip() != "fake":
        raise HTTPException(
            status_code=403,
            detail="Demo mode requires fake payment provider"
        )

    from app.services.demo_service import DemoService
    service = DemoService(db)
    result = await service.reset_demo_user()
    log_demo_reset(current_user.id, result.get("charges_created", 0), result.get("transactions_created", 0))
    return result
