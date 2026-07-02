from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.core.config import settings
from app.utils.dependencies import get_current_active_user, get_current_organization, get_current_user_role
from app.services.recurring_task_service import RecurringTaskService
from app.core.permissions import has_permission
from app.services.entitlements_service import EntitlementsService
from app.services.saas_billing_service import SaaSBillingService
from app.models.organization import Organization, OrganizationRole
from app.schemas.recurring_task import (
    RecurringTaskCreate,
    RecurringTaskResponse,
    RecurringTaskListResponse,
)
from app.models.user import User
from app.core.logging import logger

router = APIRouter(prefix="/recurring-tasks", tags=["Recurring Tasks"])


@router.post("", response_model=RecurringTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_recurring_task(
    task_data: RecurringTaskCreate,
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Create a recurring non-transactional task.

    The task only sends reminders/messages. It NEVER executes payments.
    """
    if not has_permission(role, "manage_charges"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role does not allow managing recurring tasks")
    ent_svc = EntitlementsService(db)
    await SaaSBillingService(db).ensure_free_subscription(org.id)
    entitlement = await ent_svc.can_create_recurring_task(org.id)
    if not entitlement["allowed"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=entitlement)
    service = RecurringTaskService(db)
    task = await service.create_task(current_user.id, task_data, organization_id=org.id)
    await SaaSBillingService(db).increment_usage(org.id, "recurring_tasks_created")
    return task


@router.get("", response_model=RecurringTaskListResponse)
async def list_recurring_tasks(
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """List all recurring tasks for the current user."""
    service = RecurringTaskService(db)
    tasks = await service.get_user_tasks(current_user.id, organization_id=org.id)
    return {"items": tasks, "total": len(tasks)}


@router.post("/{task_id}/cancel", response_model=RecurringTaskResponse)
async def cancel_recurring_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Cancel (deactivate) a recurring task."""
    if not has_permission(role, "manage_charges"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role does not allow managing recurring tasks")
    service = RecurringTaskService(db)
    task = await service.cancel_task(task_id, current_user.id, organization_id=org.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring task not found"
        )
    return task


@router.post("/run")
async def run_due_recurring_tasks(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger execution of due recurring tasks.

    This endpoint is protected and intended for admin/dev use.
    It only sends reminders — NEVER executes payments.
    """
    admin_emails = [e.strip() for e in settings.ADMIN_EMAILS.split(",") if e.strip()]
    if current_user.email not in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can trigger recurring task execution"
        )

    service = RecurringTaskService(db)
    due_tasks = await service.get_due_tasks()

    results = []
    for task in due_tasks:
        try:
            log = await service.execute_task(task)
            results.append({
                "task_id": task.id,
                "success": log.success,
                "message": log.message_sent[:100] if log.message_sent else None,
            })
        except Exception as e:
            logger.error(f"Error executing task {task.id}: {str(e)}")
            results.append({"task_id": task.id, "success": False, "error": str(e)})

    return {"executed": len(results), "results": results}
