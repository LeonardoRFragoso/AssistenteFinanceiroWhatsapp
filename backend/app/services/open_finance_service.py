"""
Open Finance service — Sprint 16.

Manages fake consents, connected accounts, sync operations, and audit logging.
Respects feature flags and provider fake mode. All data is org-scoped.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta, date
from typing import Optional
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.provider_foundation import OpenFinanceConsent, ConsentStatus
from app.models.open_finance import (
    ConnectedAccount, BankTransaction, FinancialCategory, OpenFinanceSyncLog,
    ConnectedAccountStatus, TransactionType, TransactionStatus,
    SyncType, SyncStatus, CategoryType,
)
from app.services.organization_audit_service import OrganizationAuditService
from app.regulated_providers.open_finance_fake import FakeOpenFinanceReadProvider

logger = logging.getLogger(__name__)


class OpenFinanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = OrganizationAuditService(db)
        self.fake_provider = FakeOpenFinanceReadProvider()

    def _check_flags(self):
        """Ensure we only operate in fake mode unless explicitly enabled."""
        if settings.ENABLE_DEMO_MODE:
            return
        if not settings.ENABLE_OPEN_FINANCE and settings.ENVIRONMENT == "production":
            raise ValueError(
                "Open Finance requires ENABLE_OPEN_FINANCE=true or demo mode"
            )

    async def create_fake_consent(
        self,
        organization_id: int,
        user_id: int,
        institution_id: str = "fake_bank",
    ) -> OpenFinanceConsent:
        """Create a fake Open Finance consent."""
        self._check_flags()

        result = await self.fake_provider.create_consent(organization_id, user_id, institution_id)
        now = datetime.now(timezone.utc)

        consent = OpenFinanceConsent(
            organization_id=organization_id,
            user_id=user_id,
            provider_name="fake",
            external_consent_id=result["consent_id"],
            status=ConsentStatus.AUTHORIZED,
            scopes=["accounts", "transactions"],
            institution_name="Fake Bank (Demo)",
            institution_code=institution_id,
            authorization_url=result["authorization_url"],
            expires_at=now + timedelta(days=365),
        )
        self.db.add(consent)
        await self.db.flush()

        await self.audit.log_event(
            organization_id=organization_id,
            action="of_consent_created",
            actor_user_id=user_id,
            resource_type="open_finance_consent",
            resource_id=str(consent.id),
            provider_type="open_finance",
            metadata={"provider": "fake", "institution_id": institution_id},
        )

        await self.db.commit()
        await self.db.refresh(consent)
        return consent

    async def list_consents(self, organization_id: int) -> list[OpenFinanceConsent]:
        """List all Open Finance consents for an organization."""
        result = await self.db.execute(
            select(OpenFinanceConsent).where(
                OpenFinanceConsent.organization_id == organization_id
            ).order_by(OpenFinanceConsent.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_consent(
        self, organization_id: int, consent_id: int, user_id: int
    ) -> Optional[OpenFinanceConsent]:
        """Revoke an Open Finance consent."""
        result = await self.db.execute(
            select(OpenFinanceConsent).where(
                OpenFinanceConsent.id == consent_id,
                OpenFinanceConsent.organization_id == organization_id,
            )
        )
        consent = result.scalar_one_or_none()
        if not consent:
            return None

        await self.fake_provider.revoke_consent(consent.external_consent_id or "")

        consent.status = ConsentStatus.REVOKED
        consent.revoked_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self.audit.log_event(
            organization_id=organization_id,
            action="of_consent_revoked",
            actor_user_id=user_id,
            resource_type="open_finance_consent",
            resource_id=str(consent.id),
            provider_type="open_finance",
            metadata={"institution_name": consent.institution_name},
        )

        await self.db.commit()
        await self.db.refresh(consent)
        return consent

    async def list_connected_accounts(self, organization_id: int) -> list[ConnectedAccount]:
        """List connected accounts for an organization."""
        result = await self.db.execute(
            select(ConnectedAccount).where(
                ConnectedAccount.organization_id == organization_id
            ).order_by(ConnectedAccount.created_at.desc())
        )
        return list(result.scalars().all())

    async def sync_fake_accounts(
        self, organization_id: int, user_id: int, consent_id: int
    ) -> list[ConnectedAccount]:
        """Sync fake connected accounts from the fake provider."""
        self._check_flags()
        started_at = datetime.now(timezone.utc)

        consent_result = await self.db.execute(
            select(OpenFinanceConsent).where(
                OpenFinanceConsent.id == consent_id,
                OpenFinanceConsent.organization_id == organization_id,
            )
        )
        consent = consent_result.scalar_one_or_none()
        if not consent:
            raise ValueError("Consent not found")

        fake_accounts = await self.fake_provider.list_accounts(
            organization_id, consent.external_consent_id or ""
        )

        created = 0
        now = datetime.now(timezone.utc)
        connected_accounts: list[ConnectedAccount] = []

        for fa in fake_accounts:
            existing = await self.db.execute(
                select(ConnectedAccount).where(
                    ConnectedAccount.organization_id == organization_id,
                    ConnectedAccount.external_account_id == fa["external_account_id"],
                )
            )
            existing_acc = existing.scalar_one_or_none()

            if existing_acc:
                existing_acc.balance_available = fa["balance_available"]
                existing_acc.balance_current = fa["balance_current"]
                existing_acc.balance_updated_at = now
                existing_acc.last_synced_at = now
                connected_accounts.append(existing_acc)
            else:
                acc = ConnectedAccount(
                    organization_id=organization_id,
                    user_id=user_id,
                    consent_id=consent_id,
                    provider_name="fake",
                    external_account_id=fa["external_account_id"],
                    institution_name=fa["institution_name"],
                    institution_code=fa["institution_code"],
                    account_type=fa["account_type"],
                    account_subtype=fa["account_subtype"],
                    account_number_masked=fa["account_number_masked"],
                    currency=fa["currency"],
                    balance_available=fa["balance_available"],
                    balance_current=fa["balance_current"],
                    balance_updated_at=now,
                    status=ConnectedAccountStatus.ACTIVE,
                    is_demo_data=True,
                    last_synced_at=now,
                )
                self.db.add(acc)
                connected_accounts.append(acc)
                created += 1

        await self.db.flush()

        sync_log = OpenFinanceSyncLog(
            organization_id=organization_id,
            consent_id=consent_id,
            sync_type=SyncType.ACCOUNTS,
            status=SyncStatus.SUCCESS,
            records_found=len(fake_accounts),
            records_created=created,
            records_updated=len(fake_accounts) - created,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
        self.db.add(sync_log)

        await self.audit.log_event(
            organization_id=organization_id,
            action="of_sync_accounts",
            actor_user_id=user_id,
            resource_type="connected_accounts",
            provider_type="open_finance",
            metadata={"accounts_created": created, "total": len(fake_accounts)},
        )

        await self.db.commit()
        for acc in connected_accounts:
            await self.db.refresh(acc)
        return connected_accounts

    async def sync_fake_transactions(
        self, organization_id: int, user_id: int
    ) -> list[BankTransaction]:
        """Sync fake bank transactions across all connected accounts."""
        self._check_flags()
        started_at = datetime.now(timezone.utc)

        accounts_result = await self.db.execute(
            select(ConnectedAccount).where(
                ConnectedAccount.organization_id == organization_id,
                ConnectedAccount.status == ConnectedAccountStatus.ACTIVE,
            )
        )
        accounts = list(accounts_result.scalars().all())
        if not accounts:
            raise ValueError("No active connected accounts found. Sync accounts first.")

        account_dicts = [
            {"external_account_id": a.external_account_id or ""}
            for a in accounts
        ]
        fake_transactions = await self.fake_provider.sync_transactions(organization_id, account_dicts)

        ext_to_db = {a.external_account_id: a for a in accounts}
        created = 0
        updated = 0
        all_transactions: list[BankTransaction] = []

        for ft in fake_transactions:
            account = ext_to_db.get(ft["external_account_id"])
            if not account:
                continue

            existing = await self.db.execute(
                select(BankTransaction).where(
                    BankTransaction.organization_id == organization_id,
                    BankTransaction.provider_name == "fake",
                    BankTransaction.external_transaction_id == ft["external_transaction_id"],
                )
            )
            existing_tx = existing.scalar_one_or_none()

            if existing_tx:
                existing_tx.amount = ft["amount"]
                existing_tx.description = ft["description"]
                existing_tx.merchant_name = ft["merchant_name"]
                existing_tx.category = ft["category"]
                updated += 1
                all_transactions.append(existing_tx)
            else:
                tx = BankTransaction(
                    organization_id=organization_id,
                    connected_account_id=account.id,
                    provider_name="fake",
                    external_transaction_id=ft["external_transaction_id"],
                    transaction_type=TransactionType(ft["transaction_type"]),
                    amount=ft["amount"],
                    currency=ft["currency"],
                    description=ft["description"],
                    merchant_name=ft["merchant_name"],
                    category=ft["category"],
                    subcategory=ft["subcategory"],
                    transaction_date=date.fromisoformat(ft["transaction_date"]),
                    posted_at=datetime.fromisoformat(ft["posted_at"]),
                    status=TransactionStatus.POSTED,
                    is_demo_data=True,
                    raw_data_sanitized=ft.get("raw_data_sanitized"),
                )
                self.db.add(tx)
                all_transactions.append(tx)
                created += 1

        await self.db.flush()

        sync_log = OpenFinanceSyncLog(
            organization_id=organization_id,
            sync_type=SyncType.TRANSACTIONS,
            status=SyncStatus.SUCCESS,
            records_found=len(fake_transactions),
            records_created=created,
            records_updated=updated,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
        self.db.add(sync_log)

        await self.audit.log_event(
            organization_id=organization_id,
            action="of_sync_transactions",
            actor_user_id=user_id,
            resource_type="bank_transactions",
            provider_type="open_finance",
            metadata={"tx_created": created, "tx_updated": updated},
        )

        await self.db.commit()
        for tx in all_transactions:
            await self.db.refresh(tx)
        return all_transactions

    async def get_sync_logs(self, organization_id: int, limit: int = 20) -> list[OpenFinanceSyncLog]:
        """Get sync logs for an organization."""
        result = await self.db.execute(
            select(OpenFinanceSyncLog).where(
                OpenFinanceSyncLog.organization_id == organization_id
            ).order_by(OpenFinanceSyncLog.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def seed_default_categories(self, organization_id: int) -> list[FinancialCategory]:
        """Seed default financial categories for an organization."""
        existing = await self.db.execute(
            select(FinancialCategory).where(
                FinancialCategory.organization_id == organization_id,
                FinancialCategory.is_system == True,
            )
        )
        if list(existing.scalars().all()):
            return []

        categories = self.fake_provider.get_categories()
        created = []
        for cat in categories:
            fc = FinancialCategory(
                organization_id=organization_id,
                name=cat["name"],
                type=CategoryType(cat["type"]),
                color=cat["color"],
                icon=cat["icon"],
                is_system=True,
            )
            self.db.add(fc)
            created.append(fc)

        await self.db.commit()
        for fc in created:
            await self.db.refresh(fc)
        return created
