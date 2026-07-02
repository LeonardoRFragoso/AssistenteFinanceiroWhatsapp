from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.core.config import settings
from app.utils.dependencies import get_current_active_user
from app.services.recurring_task_service import RecurringTaskService
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
    db: AsyncSession = Depends(get_db),
):
    """Create a recurring non-transactional task.

    The task only sends reminders/messages. It NEVER executes payments.
    """
    service = RecurringTaskService(db)
    task = await service.create_task(current_user.id, task_data)
    return task


@router.get("", response_model=RecurringTaskListResponse)
async def list_recurring_tasks(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all recurring tasks for the current user."""
    service = RecurringTaskService(db)
    tasks = await service.get_user_tasks(current_user.id)
    return {"items": tasks, "total": len(tasks)}


@router.post("/{task_id}/cancel", response_model=RecurringTaskResponse)
async def cancel_recurring_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel (deactivate) a recurring task."""
    service = RecurringTaskService(db)
    task = await service.cancel_task(task_id, current_user.id)
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
