from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.utils.dependencies import get_current_active_user, get_current_organization, get_current_user_role
from app.services.message_template_service import MessageTemplateService
from app.core.permissions import has_permission
from app.models.organization import Organization, OrganizationRole
from app.schemas.message_template import (
    MessageTemplateCreate,
    MessageTemplateUpdate,
    MessageTemplateResponse,
    MessageTemplateListResponse,
    MessageTemplatePreviewRequest,
    MessageTemplatePreviewResponse,
)
from app.models.user import User

router = APIRouter(prefix="/message-templates", tags=["Message Templates"])


@router.get("", response_model=MessageTemplateListResponse)
async def list_templates(
    active_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """List message templates for the authenticated user."""
    service = MessageTemplateService(db)
    templates = await service.list_templates(current_user.id, active_only=active_only, organization_id=org.id)
    return {"items": templates, "total": len(templates)}


@router.post("", response_model=MessageTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: MessageTemplateCreate,
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Create a new message template."""
    if not has_permission(role, "manage_templates"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role does not allow managing templates")
    service = MessageTemplateService(db)
    try:
        template = await service.create_template(current_user.id, data, organization_id=org.id)
        return template
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{template_id}", response_model=MessageTemplateResponse)
async def update_template(
    template_id: int,
    data: MessageTemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Update a message template."""
    if not has_permission(role, "manage_templates"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role does not allow managing templates")
    service = MessageTemplateService(db)
    try:
        template = await service.update_template(template_id, current_user.id, data, organization_id=org.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


@router.post("/{template_id}/preview", response_model=MessageTemplatePreviewResponse)
async def preview_template(
    template_id: int,
    data: MessageTemplatePreviewRequest,
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Preview a rendered message template with sample data."""
    service = MessageTemplateService(db)
    template = await service.get_template(template_id, current_user.id, organization_id=org.id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    rendered = service.preview_template(template, data.model_dump())
    return {
        "rendered_text": rendered,
        "template_id": template.id,
        "template_name": template.name,
    }


@router.post("/{template_id}/deactivate", response_model=MessageTemplateResponse)
async def deactivate_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    role: OrganizationRole = Depends(get_current_user_role),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a message template."""
    if not has_permission(role, "manage_templates"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role does not allow managing templates")
    service = MessageTemplateService(db)
    template = await service.deactivate_template(template_id, current_user.id, organization_id=org.id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template
