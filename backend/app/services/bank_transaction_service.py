"""
Bank transaction service — Sprint 16.

Handles listing, filtering, and aggregating bank transactions.
All queries are org-scoped. No real bank data access.
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Any
from collections import defaultdict

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.open_finance import BankTransaction, TransactionType

logger = logging.getLogger(__name__)


class BankTransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_transactions(
        self,
        organization_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        connected_account_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BankTransaction]:
        """List transactions with optional filters. Always org-scoped."""
        query = select(BankTransaction).where(
            BankTransaction.organization_id == organization_id
        )

        if start_date:
            query = query.where(BankTransaction.transaction_date >= start_date)
        if end_date:
            query = query.where(BankTransaction.transaction_date <= end_date)
        if category:
            query = query.where(BankTransaction.category == category)
        if connected_account_id:
            query = query.where(BankTransaction.connected_account_id == connected_account_id)
        if search:
            query = query.where(
                or_(
                    BankTransaction.description.ilike(f"%{search}%"),
                    BankTransaction.merchant_name.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(BankTransaction.transaction_date.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_totals(
        self,
        organization_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict[str, Decimal]:
        """Aggregate income and expense totals for an org."""
        query = select(
            func.coalesce(
                func.sum(
                    BankTransaction.amount
                ), 0
            ).label("total_amount"),
        ).where(
            BankTransaction.organization_id == organization_id
        )

        if start_date:
            query = query.where(BankTransaction.transaction_date >= start_date)
        if end_date:
            query = query.where(BankTransaction.transaction_date <= end_date)

        result = await self.db.execute(query)
        total = result.scalar() or Decimal("0")

        income = sum(
            (Decimal(str(t.amount)) for t in await self.list_transactions(
                organization_id, start_date, end_date, limit=10000
            ) if t.transaction_type == TransactionType.CREDIT),
            Decimal("0")
        )
        expense = sum(
            (Decimal(str(t.amount)) for t in await self.list_transactions(
                organization_id, start_date, end_date, limit=10000
            ) if t.transaction_type == TransactionType.DEBIT),
            Decimal("0")
        )

        return {
            "income": income,
            "expense": abs(expense),
            "net": income + expense,
        }

    async def group_by_category(
        self,
        organization_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict[str, Any]]:
        """Group transactions by category with totals."""
        transactions = await self.list_transactions(
            organization_id, start_date, end_date, limit=10000
        )

        cat_totals: dict[str, dict] = defaultdict(lambda: {"total": Decimal("0"), "count": 0})
        for t in transactions:
            cat = t.category or "Sem categoria"
            cat_totals[cat]["total"] += Decimal(str(t.amount))
            cat_totals[cat]["count"] += 1

        total_abs = sum(abs(v["total"]) for v in cat_totals.values()) or Decimal("1")
        result = []
        for cat, data in sorted(cat_totals.items(), key=lambda x: abs(x[1]["total"]), reverse=True):
            result.append({
                "category": cat,
                "total_amount": data["total"],
                "transaction_count": data["count"],
                "percentage": float(abs(data["total"]) / total_abs * 100),
            })
        return result

    async def group_by_merchant(
        self,
        organization_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[dict[str, Any]]:
        """Group transactions by merchant with totals."""
        transactions = await self.list_transactions(
            organization_id, start_date, end_date, limit=10000
        )

        merchant_totals: dict[str, dict] = defaultdict(lambda: {"total": Decimal("0"), "count": 0})
        for t in transactions:
            merchant = t.merchant_name or "Desconhecido"
            merchant_totals[merchant]["total"] += Decimal(str(t.amount))
            merchant_totals[merchant]["count"] += 1

        result = []
        for merchant, data in sorted(merchant_totals.items(), key=lambda x: abs(x[1]["total"]), reverse=True):
            result.append({
                "merchant": merchant,
                "total_amount": data["total"],
                "transaction_count": data["count"],
            })
        return result

    async def get_largest_expense(
        self,
        organization_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[BankTransaction]:
        """Get the largest expense transaction in the period."""
        transactions = await self.list_transactions(
            organization_id, start_date, end_date, limit=10000
        )
        debits = [t for t in transactions if t.transaction_type == TransactionType.DEBIT]
        if not debits:
            return None
        return min(debits, key=lambda t: Decimal(str(t.amount)))
