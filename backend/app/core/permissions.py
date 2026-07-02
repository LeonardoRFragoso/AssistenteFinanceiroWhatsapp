from fastapi import HTTPException, status
from app.models.organization import OrganizationRole
from app.services.organization_service import OrganizationService
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Set


PERMISSIONS: dict[str, Set[OrganizationRole]] = {
    "view_dashboard": {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.FINANCE, OrganizationRole.VIEWER},
    "manage_charges": {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.FINANCE},
    "manage_customers": {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.FINANCE},
    "manage_templates": {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.FINANCE},
    "manage_collection_rules": {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.FINANCE},
    "view_analytics": {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.FINANCE, OrganizationRole.VIEWER},
    "export_data": {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.FINANCE},
    "manage_members": {OrganizationRole.OWNER, OrganizationRole.ADMIN},
    "manage_settings": {OrganizationRole.OWNER, OrganizationRole.ADMIN},
}


def has_permission(role: OrganizationRole, permission: str) -> bool:
    allowed = PERMISSIONS.get(permission, set())
    return role in allowed


async def require_permission(
    permission: str,
    org_id: int,
    user_id: int,
    db: AsyncSession,
) -> None:
    """Raise 403 if the user lacks the required permission in the organization."""
    service = OrganizationService(db)
    role = await service.get_user_role(org_id, user_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )
    if not has_permission(role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your role ({role.value}) does not have permission: {permission}",
        )
