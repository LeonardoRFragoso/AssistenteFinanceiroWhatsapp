"""
Financial summary service — Sprint 16.

Generates monthly financial summaries using fake/demo data.
Does NOT provide investment advice or credit recommendations.
Uses informative language only.
"""
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.open_finance import ConnectedAccount, BankTransaction, TransactionType
from app.services.bank_transaction_service import BankTransactionService

logger = logging.getLogger(__name__)


class FinancialSummaryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tx_service = BankTransactionService(db)

    async def get_monthly_summary(
        self,
        organization_id: int,
        year: int,
        month: int,
    ) -> dict[str, Any]:
        """Generate a monthly financial summary for an organization."""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        # Get total balances across all accounts
        accounts_result = await self.db.execute(
            select(ConnectedAccount).where(
                ConnectedAccount.organization_id == organization_id,
                ConnectedAccount.status == "active",
            )
        )
        accounts = list(accounts_result.scalars().all())

        total_available = sum(
            (Decimal(str(a.balance_available or 0)) for a in accounts),
            Decimal("0")
        )
        total_current = sum(
            (Decimal(str(a.balance_current or 0)) for a in accounts),
            Decimal("0")
        )

        # Get transactions for the month
        transactions = await self.tx_service.list_transactions(
            organization_id, start_date, end_date, limit=10000
        )

        income_total = sum(
            (Decimal(str(t.amount)) for t in transactions if t.transaction_type == TransactionType.CREDIT),
            Decimal("0")
        )
        expense_total = sum(
            (abs(Decimal(str(t.amount))) for t in transactions if t.transaction_type == TransactionType.DEBIT),
            Decimal("0")
        )
        net_flow = income_total - expense_total

        # Top categories
        top_categories = await self.tx_service.group_by_category(
            organization_id, start_date, end_date
        )

        # Top merchants
        top_merchants = await self.tx_service.group_by_merchant(
            organization_id, start_date, end_date
        )

        # Largest expense
        largest_expense = await self.tx_service.get_largest_expense(
            organization_id, start_date, end_date
        )

        # Generate safe textual insight
        insight = self._generate_insight(
            income_total, expense_total, net_flow,
            top_categories[:3] if top_categories else [],
            is_demo=all(a.is_demo_data for a in accounts) if accounts else True,
        )

        return {
            "total_balance_available": total_available,
            "total_balance_current": total_current,
            "income_total": income_total,
            "expense_total": expense_total,
            "net_flow": net_flow,
            "top_categories": top_categories[:5],
            "top_merchants": top_merchants[:5],
            "largest_expense": largest_expense,
            "transaction_count": len(transactions),
            "is_demo_data": True,
            "period_start": start_date,
            "period_end": end_date,
            "insight": insight,
        }

    def _generate_insight(
        self,
        income: Decimal,
        expense: Decimal,
        net: Decimal,
        top_categories: list[dict],
        is_demo: bool = True,
    ) -> str:
        """Generate a safe, informative insight. No investment advice."""
        parts = []

        if is_demo:
            parts.append("[Dados de demonstração]")

        parts.append(f"Você teve R$ {float(expense):.2f} em saídas no período.")

        if income > 0:
            parts.append(f"Entradas: R$ {float(income):.2f}.")

        if net >= 0:
            parts.append(f"Saldo positivo de R$ {float(net):.2f}.")
        else:
            parts.append(f"Saldo negativo de R$ {float(abs(net)):.2f}.")

        if top_categories:
            top_cat = top_categories[0]
            parts.append(f"A maior categoria foi {top_cat['category']}.")

        return " ".join(parts)

    async def get_balance_summary(self, organization_id: int) -> dict[str, Any]:
        """Get current balance summary across all connected accounts."""
        accounts_result = await self.db.execute(
            select(ConnectedAccount).where(
                ConnectedAccount.organization_id == organization_id,
                ConnectedAccount.status == "active",
            )
        )
        accounts = list(accounts_result.scalars().all())

        total_available = sum(
            (Decimal(str(a.balance_available or 0)) for a in accounts),
            Decimal("0")
        )
        total_current = sum(
            (Decimal(str(a.balance_current or 0)) for a in accounts),
            Decimal("0")
        )

        is_demo = all(a.is_demo_data for a in accounts) if accounts else True

        return {
            "total_balance_available": total_available,
            "total_balance_current": total_current,
            "accounts_count": len(accounts),
            "is_demo_data": is_demo,
            "accounts": [
                {
                    "id": a.id,
                    "institution_name": a.institution_name,
                    "account_number_masked": a.account_number_masked,
                    "balance_available": a.balance_available,
                    "balance_current": a.balance_current,
                }
                for a in accounts
            ],
        }
