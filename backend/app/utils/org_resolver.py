from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.organization_service import OrganizationService


async def resolve_organization_id(db: AsyncSession, user_id: int, organization_id: Optional[int]) -> int:
    """Resolve organization_id: if None, look up the user's default org.

    Raises ValueError if the user has no default organization.
    """
    if organization_id is not None:
        return organization_id
    org_service = OrganizationService(db)
    org = await org_service.get_default_organization(user_id)
    if org is None:
        org = await org_service.ensure_default_organization(
            await _get_user(db, user_id)
        )
    return org.id


async def _get_user(db: AsyncSession, user_id: int):
    from app.models.user import User
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
