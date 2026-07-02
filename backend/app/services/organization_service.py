from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.user import User
from app.core.logging import logger
import re


def _slugify(name: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
    slug = re.sub(r'[\s-]+', '-', slug).strip('-')
    return slug or f"org-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_default_organization(self, user: User) -> Organization:
        """Create a default personal organization for a user."""
        existing = await self.db.execute(
            select(Organization).where(Organization.owner_user_id == user.id)
        )
        org = existing.scalar_one_or_none()
        if org:
            return org

        slug = _slugify(user.name)
        # Ensure slug uniqueness
        slug_check = await self.db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        if slug_check.scalar_one_or_none():
            slug = f"{slug}-{user.id}"

        org = Organization(
            name=f"{user.name}'s Workspace",
            slug=slug,
            owner_user_id=user.id,
            email=user.email,
            phone=user.phone_number,
            active=True,
        )
        self.db.add(org)
        await self.db.flush()

        member = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=OrganizationRole.OWNER,
            active=True,
            joined_at=datetime.now(timezone.utc),
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(org)
        logger.info(f"Default organization created for user {user.id}: {org.slug}")
        return org

    async def list_user_organizations(self, user_id: int) -> List[Dict[str, Any]]:
        """List all organizations a user is a member of."""
        result = await self.db.execute(
            select(Organization, OrganizationMember.role)
            .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
            .where(
                and_(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.active == True,
                    Organization.active == True,
                )
            )
            .order_by(Organization.name)
        )
        rows = result.all()
        return [
            {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "role": role.value if hasattr(role, 'value') else str(role),
                "owner_user_id": org.owner_user_id,
                "email": org.email,
                "phone": org.phone,
                "active": org.active,
            }
            for org, role in rows
        ]

    async def get_organization(self, org_id: int) -> Optional[Organization]:
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_user_role(self, org_id: int, user_id: int) -> Optional[OrganizationRole]:
        result = await self.db.execute(
            select(OrganizationMember.role).where(
                and_(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.active == True,
                )
            )
        )
        row = result.scalar_one_or_none()
        return row

    async def get_default_organization(self, user_id: int) -> Optional[Organization]:
        """Get the user's default (owned) organization."""
        result = await self.db.execute(
            select(Organization).where(Organization.owner_user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def ensure_default_organization(self, user: User) -> Organization:
        """Ensure user has a default organization, create if missing."""
        org = await self.get_default_organization(user.id)
        if org:
            # Ensure membership exists
            member = await self.get_user_role(org.id, user.id)
            if member is None:
                self.db.add(OrganizationMember(
                    organization_id=org.id,
                    user_id=user.id,
                    role=OrganizationRole.OWNER,
                    active=True,
                    joined_at=datetime.now(timezone.utc),
                ))
                await self.db.commit()
            return org
        return await self.create_default_organization(user)

    async def create_organization(
        self,
        name: str,
        owner: User,
        document: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Organization:
        slug = _slugify(name)
        slug_check = await self.db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        if slug_check.scalar_one_or_none():
            slug = f"{slug}-{owner.id}"

        org = Organization(
            name=name,
            slug=slug,
            owner_user_id=owner.id,
            document=document,
            email=email,
            phone=phone,
            active=True,
        )
        self.db.add(org)
        await self.db.flush()

        member = OrganizationMember(
            organization_id=org.id,
            user_id=owner.id,
            role=OrganizationRole.OWNER,
            active=True,
            joined_at=datetime.now(timezone.utc),
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def update_organization(
        self,
        org_id: int,
        name: Optional[str] = None,
        document: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[Organization]:
        org = await self.get_organization(org_id)
        if not org:
            return None
        if name is not None:
            org.name = name
        if document is not None:
            org.document = document
        if email is not None:
            org.email = email
        if phone is not None:
            org.phone = phone
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def list_members(self, org_id: int) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(OrganizationMember, User)
            .outerjoin(User, User.id == OrganizationMember.user_id)
            .where(OrganizationMember.organization_id == org_id)
            .order_by(OrganizationMember.created_at)
        )
        rows = result.all()
        return [
            {
                "id": member.id,
                "organization_id": member.organization_id,
                "user_id": member.user_id,
                "role": member.role.value if hasattr(member.role, 'value') else str(member.role),
                "active": member.active,
                "invited_email": member.invited_email,
                "invited_at": member.invited_at.isoformat() if member.invited_at else None,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "user_name": user.name if user else None,
                "user_email": user.email if user else None,
            }
            for member, user in rows
        ]

    async def add_member(
        self,
        org_id: int,
        email: str,
        role: OrganizationRole = OrganizationRole.VIEWER,
    ) -> OrganizationMember:
        """Add a member by email. If user exists, link immediately. Otherwise, create pending invite."""
        user_result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = user_result.scalar_one_or_none()

        member = OrganizationMember(
            organization_id=org_id,
            user_id=user.id if user else None,
            role=role,
            active=True,
            invited_email=email,
            invited_at=datetime.now(timezone.utc),
            joined_at=datetime.now(timezone.utc) if user else None,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def update_member_role(
        self,
        org_id: int,
        member_id: int,
        new_role: OrganizationRole,
    ) -> Optional[OrganizationMember]:
        result = await self.db.execute(
            select(OrganizationMember).where(
                and_(
                    OrganizationMember.id == member_id,
                    OrganizationMember.organization_id == org_id,
                )
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return None
        member.role = new_role
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def deactivate_member(
        self,
        org_id: int,
        member_id: int,
    ) -> Optional[OrganizationMember]:
        result = await self.db.execute(
            select(OrganizationMember).where(
                and_(
                    OrganizationMember.id == member_id,
                    OrganizationMember.organization_id == org_id,
                )
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return None
        member.active = False
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def check_permission(
        self,
        org_id: int,
        user_id: int,
        required_role: OrganizationRole,
    ) -> bool:
        """Check if user has the required role or higher in the organization."""
        role = await self.get_user_role(org_id, user_id)
        if role is None:
            return False

        role_hierarchy = {
            OrganizationRole.OWNER: 4,
            OrganizationRole.ADMIN: 3,
            OrganizationRole.FINANCE: 2,
            OrganizationRole.VIEWER: 1,
        }
        return role_hierarchy.get(role, 0) >= role_hierarchy.get(required_role, 0)
