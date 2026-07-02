import pytest
from app.services.organization_service import OrganizationService
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.user import User
from app.models.charge import Charge, ChargeStatus
from app.core.permissions import has_permission, require_permission, PERMISSIONS
from fastapi import HTTPException
from decimal import Decimal
from datetime import date


@pytest.fixture
async def second_user(db_session):
    user = User(
        name="Maria Santos",
        email="maria@example.com",
        hashed_password="hashed",
        phone_number="+5511888888888",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestOrganizationService:
    async def test_create_default_organization(self, db_session, sample_user):
        service = OrganizationService(db_session)
        org = await service.create_default_organization(sample_user)

        assert org.id is not None
        assert org.name == "João Empresário's Workspace"
        assert org.owner_user_id == sample_user.id
        assert org.active is True

    async def test_create_default_organization_is_idempotent(self, db_session, sample_user):
        service = OrganizationService(db_session)
        org1 = await service.create_default_organization(sample_user)
        org2 = await service.create_default_organization(sample_user)
        assert org1.id == org2.id

    async def test_ensure_default_organization_creates_if_missing(self, db_session, sample_user):
        service = OrganizationService(db_session)
        org = await service.ensure_default_organization(sample_user)
        assert org is not None
        assert org.owner_user_id == sample_user.id

    async def test_list_user_organizations(self, db_session, sample_user):
        service = OrganizationService(db_session)
        await service.create_default_organization(sample_user)
        orgs = await service.list_user_organizations(sample_user.id)
        assert len(orgs) == 1
        assert orgs[0]["name"] == "João Empresário's Workspace"
        assert orgs[0]["role"] == "owner"

    async def test_get_user_role(self, db_session, sample_user):
        service = OrganizationService(db_session)
        org = await service.create_default_organization(sample_user)
        role = await service.get_user_role(org.id, sample_user.id)
        assert role == OrganizationRole.OWNER

    async def test_get_user_role_returns_none_for_non_member(self, db_session, sample_user, second_user):
        service = OrganizationService(db_session)
        org = await service.create_default_organization(sample_user)
        role = await service.get_user_role(org.id, second_user.id)
        assert role is None

    async def test_create_organization(self, db_session, sample_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(
            name="Acme Corp",
            owner=sample_user,
            document="12345678000199",
            email="contato@acme.com",
            phone="+551133334444",
        )
        assert org.name == "Acme Corp"
        assert org.slug == "acme-corp"
        assert org.document == "12345678000199"
        assert org.email == "contato@acme.com"

    async def test_update_organization(self, db_session, sample_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(name="Test Org", owner=sample_user)
        updated = await service.update_organization(org.id, name="Updated Org", phone="+5511999999999")
        assert updated.name == "Updated Org"
        assert updated.phone == "+5511999999999"

    async def test_add_member_existing_user(self, db_session, sample_user, second_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(name="Test Org", owner=sample_user)
        member = await service.add_member(org.id, second_user.email, OrganizationRole.FINANCE)
        assert member.user_id == second_user.id
        assert member.role == OrganizationRole.FINANCE
        assert member.active is True

    async def test_add_member_nonexistent_user(self, db_session, sample_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(name="Test Org", owner=sample_user)
        member = await service.add_member(org.id, "nonexistent@example.com", OrganizationRole.VIEWER)
        assert member.user_id is None
        assert member.invited_email == "nonexistent@example.com"

    async def test_update_member_role(self, db_session, sample_user, second_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(name="Test Org", owner=sample_user)
        member = await service.add_member(org.id, second_user.email, OrganizationRole.VIEWER)
        updated = await service.update_member_role(org.id, member.id, OrganizationRole.ADMIN)
        assert updated.role == OrganizationRole.ADMIN

    async def test_deactivate_member(self, db_session, sample_user, second_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(name="Test Org", owner=sample_user)
        member = await service.add_member(org.id, second_user.email, OrganizationRole.VIEWER)
        deactivated = await service.deactivate_member(org.id, member.id)
        assert deactivated.active is False

    async def test_list_members(self, db_session, sample_user, second_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(name="Test Org", owner=sample_user)
        await service.add_member(org.id, second_user.email, OrganizationRole.FINANCE)
        members = await service.list_members(org.id)
        assert len(members) == 2  # owner + new member
        roles = [m["role"] for m in members]
        assert "owner" in roles
        assert "finance" in roles

    async def test_check_permission_owner(self, db_session, sample_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(name="Test Org", owner=sample_user)
        assert await service.check_permission(org.id, sample_user.id, OrganizationRole.OWNER) is True
        assert await service.check_permission(org.id, sample_user.id, OrganizationRole.ADMIN) is True
        assert await service.check_permission(org.id, sample_user.id, OrganizationRole.VIEWER) is True

    async def test_check_permission_viewer(self, db_session, sample_user, second_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(name="Test Org", owner=sample_user)
        await service.add_member(org.id, second_user.email, OrganizationRole.VIEWER)
        assert await service.check_permission(org.id, second_user.id, OrganizationRole.VIEWER) is True
        assert await service.check_permission(org.id, second_user.id, OrganizationRole.ADMIN) is False
        assert await service.check_permission(org.id, second_user.id, OrganizationRole.OWNER) is False

    async def test_check_permission_non_member(self, db_session, sample_user, second_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(name="Test Org", owner=sample_user)
        assert await service.check_permission(org.id, second_user.id, OrganizationRole.VIEWER) is False


class TestPermissions:
    def test_has_permission_owner_can_do_everything(self):
        for perm in PERMISSIONS:
            assert has_permission(OrganizationRole.OWNER, perm) is True

    def test_has_permission_viewer_cannot_manage(self):
        assert has_permission(OrganizationRole.VIEWER, "manage_charges") is False
        assert has_permission(OrganizationRole.VIEWER, "manage_members") is False
        assert has_permission(OrganizationRole.VIEWER, "manage_settings") is False
        assert has_permission(OrganizationRole.VIEWER, "export_data") is False

    def test_has_permission_viewer_can_view(self):
        assert has_permission(OrganizationRole.VIEWER, "view_dashboard") is True
        assert has_permission(OrganizationRole.VIEWER, "view_analytics") is True

    def test_has_permission_finance_can_manage_charges(self):
        assert has_permission(OrganizationRole.FINANCE, "manage_charges") is True
        assert has_permission(OrganizationRole.FINANCE, "manage_customers") is True
        assert has_permission(OrganizationRole.FINANCE, "export_data") is True

    def test_has_permission_finance_cannot_manage_members(self):
        assert has_permission(OrganizationRole.FINANCE, "manage_members") is False
        assert has_permission(OrganizationRole.FINANCE, "manage_settings") is False

    def test_has_permission_admin_can_manage_members(self):
        assert has_permission(OrganizationRole.ADMIN, "manage_members") is True
        assert has_permission(OrganizationRole.ADMIN, "manage_settings") is True

    async def test_require_permission_raises_for_non_member(self, db_session, sample_user, second_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(name="Test Org", owner=sample_user)
        with pytest.raises(HTTPException) as exc_info:
            await require_permission("view_dashboard", org.id, second_user.id, db_session)
        assert exc_info.value.status_code == 403

    async def test_require_permission_raises_for_insufficient_role(self, db_session, sample_user, second_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(name="Test Org", owner=sample_user)
        await service.add_member(org.id, second_user.email, OrganizationRole.VIEWER)
        with pytest.raises(HTTPException) as exc_info:
            await require_permission("manage_members", org.id, second_user.id, db_session)
        assert exc_info.value.status_code == 403

    async def test_require_permission_passes_for_adequate_role(self, db_session, sample_user):
        service = OrganizationService(db_session)
        org = await service.create_organization(name="Test Org", owner=sample_user)
        await require_permission("manage_members", org.id, sample_user.id, db_session)


class TestMultiTenantIsolation:
    async def test_charge_with_organization_id(self, db_session, sample_user):
        service = OrganizationService(db_session)
        org = await service.create_default_organization(sample_user)
        charge = Charge(
            user_id=sample_user.id,
            organization_id=org.id,
            customer_name="Test Customer",
            amount=Decimal("100.00"),
            provider="fake",
            status=ChargeStatus.PENDING,
        )
        db_session.add(charge)
        await db_session.commit()
        await db_session.refresh(charge)
        assert charge.organization_id == org.id

    async def test_charges_isolated_by_organization(self, db_session, sample_user, second_user):
        service = OrganizationService(db_session)
        org1 = await service.create_organization(name="Org 1", owner=sample_user)
        org2 = await service.create_organization(name="Org 2", owner=second_user)

        charge1 = Charge(
            user_id=sample_user.id,
            organization_id=org1.id,
            customer_name="Customer A",
            amount=Decimal("100.00"),
            provider="fake",
            status=ChargeStatus.PENDING,
        )
        charge2 = Charge(
            user_id=second_user.id,
            organization_id=org2.id,
            customer_name="Customer B",
            amount=Decimal("200.00"),
            provider="fake",
            status=ChargeStatus.PENDING,
        )
        db_session.add_all([charge1, charge2])
        await db_session.commit()

        from sqlalchemy import select
        result1 = await db_session.execute(
            select(Charge).where(Charge.organization_id == org1.id)
        )
        charges1 = result1.scalars().all()
        assert len(charges1) == 1
        assert charges1[0].customer_name == "Customer A"

        result2 = await db_session.execute(
            select(Charge).where(Charge.organization_id == org2.id)
        )
        charges2 = result2.scalars().all()
        assert len(charges2) == 1
        assert charges2[0].customer_name == "Customer B"

    async def test_organization_cascade_delete(self, db_session, sample_user):
        service = OrganizationService(db_session)
        org = await service.create_default_organization(sample_user)
        await service.add_member(org.id, "test@example.com", OrganizationRole.VIEWER)

        # ORM-level delete triggers cascade="all, delete-orphan"
        await db_session.delete(org)
        await db_session.commit()

        from sqlalchemy import select
        result = await db_session.execute(
            select(OrganizationMember).where(OrganizationMember.organization_id == org.id)
        )
        members = result.scalars().all()
        assert len(members) == 0
