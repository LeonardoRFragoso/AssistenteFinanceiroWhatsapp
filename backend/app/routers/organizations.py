from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import get_db
from app.utils.dependencies import get_current_active_user, get_current_organization, get_current_user_role
from app.core.permissions import require_permission, has_permission
from app.models.user import User
from app.models.organization import Organization, OrganizationRole
from app.services.organization_service import OrganizationService
from app.services.entitlements_service import EntitlementsService
from app.services.saas_billing_service import SaaSBillingService
from datetime import datetime, timezone

router = APIRouter(prefix="/organizations", tags=["Organizations"])


class OrganizationCreate(BaseModel):
    name: str
    document: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    document: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class MemberAdd(BaseModel):
    email: str
    role: str = "viewer"


class MemberUpdate(BaseModel):
    role: str


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    owner_user_id: int
    document: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    active: bool
    role: Optional[str] = None

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    id: int
    organization_id: int
    user_id: Optional[int] = None
    role: str
    active: bool
    invited_email: Optional[str] = None
    invited_at: Optional[str] = None
    joined_at: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None


@router.get("")
async def list_organizations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all organizations the current user is a member of."""
    service = OrganizationService(db)
    orgs = await service.list_user_organizations(current_user.id)
    return {"items": orgs}


@router.post("")
async def create_organization(
    data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization. The creator becomes the owner."""
    service = OrganizationService(db)
    org = await service.create_organization(
        name=data.name,
        owner=current_user,
        document=data.document,
        email=data.email,
        phone=data.phone,
    )
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "owner_user_id": org.owner_user_id,
        "active": org.active,
    }


@router.get("/{org_id}")
async def get_organization(
    org_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific organization. User must be a member."""
    service = OrganizationService(db)
    org = await service.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    role = await service.get_user_role(org.id, current_user.id)
    if role is None:
        raise HTTPException(status_code=403, detail="You are not a member of this organization")
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "owner_user_id": org.owner_user_id,
        "document": org.document,
        "email": org.email,
        "phone": org.phone,
        "active": org.active,
        "role": role.value if hasattr(role, 'value') else str(role),
    }


@router.put("/{org_id}")
async def update_organization(
    org_id: int,
    data: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update organization settings. Requires manage_settings permission."""
    service = OrganizationService(db)
    org = await service.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    await require_permission("manage_settings", org.id, current_user.id, db)
    updated = await service.update_organization(
        org.id,
        name=data.name,
        document=data.document,
        email=data.email,
        phone=data.phone,
    )
    return {
        "id": updated.id,
        "name": updated.name,
        "slug": updated.slug,
        "document": updated.document,
        "email": updated.email,
        "phone": updated.phone,
    }


@router.get("/{org_id}/members")
async def list_members(
    org_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List members of an organization. User must be a member."""
    service = OrganizationService(db)
    org = await service.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    role = await service.get_user_role(org.id, current_user.id)
    if role is None:
        raise HTTPException(status_code=403, detail="You are not a member of this organization")
    members = await service.list_members(org.id)
    return {"items": members}


@router.post("/{org_id}/members")
async def add_member(
    org_id: int,
    data: MemberAdd,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a member to the organization. Requires manage_members permission."""
    service = OrganizationService(db)
    org = await service.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    await require_permission("manage_members", org.id, current_user.id, db)

    try:
        role = OrganizationRole(data.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {data.role}")

    # Cannot add an owner via this endpoint
    if role == OrganizationRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot add owner via member invitation")

    ent_svc = EntitlementsService(db)
    await SaaSBillingService(db).ensure_free_subscription(org.id)
    entitlement = await ent_svc.can_add_team_member(org.id)
    if not entitlement["allowed"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=entitlement)

    member = await service.add_member(org.id, data.email, role)
    return {
        "id": member.id,
        "organization_id": member.organization_id,
        "user_id": member.user_id,
        "role": member.role.value if hasattr(member.role, 'value') else str(member.role),
        "invited_email": member.invited_email,
        "active": member.active,
    }


@router.put("/{org_id}/members/{member_id}")
async def update_member(
    org_id: int,
    member_id: int,
    data: MemberUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a member's role. Requires manage_members permission."""
    service = OrganizationService(db)
    org = await service.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    await require_permission("manage_members", org.id, current_user.id, db)

    try:
        new_role = OrganizationRole(data.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {data.role}")

    if new_role == OrganizationRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot assign owner role")

    member = await service.update_member_role(org.id, member_id, new_role)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return {
        "id": member.id,
        "role": member.role.value if hasattr(member.role, 'value') else str(member.role),
        "active": member.active,
    }


@router.post("/{org_id}/members/{member_id}/deactivate")
async def deactivate_member(
    org_id: int,
    member_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a member. Requires manage_members permission."""
    service = OrganizationService(db)
    org = await service.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    await require_permission("manage_members", org.id, current_user.id, db)

    # Check member exists and is not the owner
    members = await service.list_members(org.id)
    target = next((m for m in members if m["id"] == member_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    if target["role"] == "owner":
        raise HTTPException(status_code=400, detail="Cannot deactivate the owner")

    member = await service.deactivate_member(org.id, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"id": member.id, "active": member.active}
