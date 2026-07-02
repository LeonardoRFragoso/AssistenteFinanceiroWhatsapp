from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.utils.dependencies import get_current_active_user
from app.services.collection_service import CollectionService
from app.schemas.collection_rule import (
    CollectionRuleCreate,
    CollectionRuleResponse,
    CollectionRuleListResponse,
    CollectionMessageLogListResponse,
    FollowupPreviewResponse,
)
from app.models.user import User

router = APIRouter(prefix="/collection", tags=["Collection Rules"])


@router.get("/rules", response_model=CollectionRuleListResponse)
async def list_rules(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List collection rules for the authenticated user."""
    service = CollectionService(db)
    rules = await service.list_rules(current_user.id)
    return {"items": rules, "total": len(rules)}


@router.post("/rules", response_model=CollectionRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    data: CollectionRuleCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a collection rule."""
    service = CollectionService(db)
    try:
        rule = await service.create_rule(current_user.id, data)
        return rule
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/rules/{rule_id}/deactivate", response_model=CollectionRuleResponse)
async def deactivate_rule(
    rule_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a collection rule."""
    service = CollectionService(db)
    rule = await service.deactivate_rule(rule_id, current_user.id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return rule


@router.get("/followups/overdue", response_model=FollowupPreviewResponse)
async def get_overdue_followups(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate draft follow-up messages for overdue charges.

    Does NOT send any messages. Returns previews only.
    Sending requires explicit user confirmation.
    """
    service = CollectionService(db)
    result = await service.generate_followup_previews(current_user.id, limit=limit)
    return result


@router.get("/logs", response_model=CollectionMessageLogListResponse)
async def list_logs(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List recent collection message logs."""
    service = CollectionService(db)
    logs = await service.list_logs(current_user.id, limit=limit)
    return {"items": logs, "total": len(logs)}
