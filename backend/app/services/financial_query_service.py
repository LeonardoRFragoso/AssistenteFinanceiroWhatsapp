from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from app.repositories.charge_repository import ChargeRepository
from app.services.charge_service import ChargeService
from app.core.logging import logger


class FinancialQueryService:
    """Dedicated service for financial queries via WhatsApp.

    Handles charge lookups by status, customer, period, and generates
    formatted WhatsApp responses. Never executes payments or bank operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self.charge_service = ChargeService(db)

    async def list_overdue_charges(self, user_id: int) -> str:
        charges = await self.charge_repo.get_overdue_by_user(user_id)
        if not charges:
            return "✅ Você não tem cobranças vencidas."

        total = sum(float(c.amount) for c in charges)
        message = f"⚠️ Você tem {len(charges)} cobrança(s) vencida(s), totalizando R$ {total:.2f}:\n\n"
        for i, c in enumerate(charges, 1):
            due_str = c.due_date.strftime("%d/%m/%Y") if c.due_date else "sem vencimento"
            message += f"{i}. {c.customer_name} — R$ {float(c.amount):.2f} — venceu em {due_str}\n"

        message += "\nQuer que eu prepare uma mensagem de cobrança para algum deles?"
        return message

    async def list_pending_charges(self, user_id: int) -> str:
        charges = await self.charge_repo.get_pending_by_user(user_id)
        if not charges:
            return "✅ Você não tem cobranças pendentes."

        today = date.today()
        pending_only = [c for c in charges if not c.due_date or c.due_date >= today]
        if not pending_only:
            return "✅ Você não tem cobranças pendentes (todas as pendentes estão vencidas)."

        total = sum(float(c.amount) for c in pending_only)
        message = f"⏳ Você tem {len(pending_only)} cobrança(s) pendente(s), totalizando R$ {total:.2f}:\n\n"
        for i, c in enumerate(pending_only, 1):
            due_str = c.due_date.strftime("%d/%m/%Y") if c.due_date else "sem vencimento"
            message += f"{i}. {c.customer_name} — R$ {float(c.amount):.2f} — vence: {due_str}\n"

        return message

    async def list_paid_charges(self, user_id: int, limit: int = 10) -> str:
        charges = await self.charge_repo.get_paid_by_user(user_id, limit=limit)
        if not charges:
            return "Você ainda não tem cobranças pagas."

        total = sum(float(c.amount) for c in charges)
        message = f"💰 Você tem {len(charges)} cobrança(s) paga(s), totalizando R$ {total:.2f}:\n\n"
        for i, c in enumerate(charges, 1):
            paid_str = c.paid_at.strftime("%d/%m/%Y") if c.paid_at else "data não disponível"
            message += f"{i}. {c.customer_name} — R$ {float(c.amount):.2f} — pago em {paid_str}\n"

        return message

    async def search_charges_by_customer(self, user_id: int, customer_name: str) -> str:
        charges = await self.charge_repo.find_by_customer_name(user_id, customer_name)
        if not charges:
            return f"Não encontrei cobranças para o cliente \"{customer_name}\"."

        message = f"🔍 Cobranças de \"{customer_name}\" ({len(charges)} resultado(s)):\n\n"
        for i, c in enumerate(charges, 1):
            derived = self.charge_service.get_derived_status(c)
            status_label = {
                "pending": "pendente",
                "paid": "pago",
                "overdue": "vencida",
                "cancelled": "cancelada",
                "expired": "expirada",
                "failed": "falhou"
            }.get(derived, derived)
            message += f"{i}. R$ {float(c.amount):.2f} — {status_label}"
            if c.due_date:
                message += f" (vence: {c.due_date.strftime('%d/%m/%Y')})"
            message += "\n"

        return message

    async def charge_summary(self, user_id: int) -> str:
        summary = await self.charge_service.get_summary(user_id)

        message = "📊 *Resumo de cobranças:*\n\n"
        message += f"⏳ Pendentes: {summary.count_pending} — R$ {float(summary.total_pending):.2f}\n"
        message += f"⚠️ Vencidas: {summary.count_overdue} — R$ {float(summary.total_overdue):.2f}\n"
        message += f"💰 Pagas: {summary.count_paid} — R$ {float(summary.total_paid):.2f}\n"
        message += f"❌ Canceladas: {summary.count_cancelled}\n\n"
        message += f"📌 Total a receber: R$ {float(summary.total_receivable):.2f}"

        return message

    async def customer_charge_history(self, user_id: int, customer_name: str) -> str:
        charges = await self.charge_repo.find_by_customer_name(user_id, customer_name)
        if not charges:
            return f"Não encontrei histórico para o cliente \"{customer_name}\"."

        total_paid = sum(float(c.amount) for c in charges if c.status.value == "paid")
        total_pending = sum(float(c.amount) for c in charges if c.status.value == "pending")
        total_overdue = sum(
            float(c.amount) for c in charges
            if c.status.value == "pending" and c.due_date and c.due_date < date.today()
        )

        message = f"📋 *Histórico de {customer_name}:*\n\n"
        message += f"Total de cobranças: {len(charges)}\n"
        message += f"💰 Pago: R$ {total_paid:.2f}\n"
        message += f"⏳ Pendente: R$ {total_pending:.2f}\n"
        if total_overdue > 0:
            message += f"⚠️ Vencido: R$ {total_overdue:.2f}\n"
        message += "\nÚltimas cobranças:\n"
        for c in charges[:5]:
            derived = self.charge_service.get_derived_status(c)
            message += f"  • R$ {float(c.amount):.2f} — {derived}\n"

        return message

    async def monthly_financial_summary(
        self, user_id: int, year: int, month: int
    ) -> str:
        """Generate a monthly financial summary for charges."""
        from sqlalchemy import select, and_, extract, func, case
        from app.models.charge import Charge, ChargeStatus

        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year, 12, 31)
        else:
            end_date = date(year, month + 1, 1)

        query = select(
            func.coalesce(
                func.sum(
                    case(
                        (Charge.status == ChargeStatus.PAID, Charge.amount),
                        else_=0
                    )
                ), 0
            ).label("total_paid"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Charge.status == ChargeStatus.PENDING,
                                Charge.due_date.is_(None) | (Charge.due_date >= date.today())
                            ),
                            Charge.amount
                        ),
                        else_=0
                    )
                ), 0
            ).label("total_pending"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Charge.status == ChargeStatus.PENDING,
                                Charge.due_date.isnot(None),
                                Charge.due_date < date.today()
                            ),
                            Charge.amount
                        ),
                        else_=0
                    )
                ), 0
            ).label("total_overdue"),
            func.coalesce(
                func.sum(
                    case(
                        (Charge.status == ChargeStatus.CANCELLED, Charge.amount),
                        else_=0
                    )
                ), 0
            ).label("total_cancelled"),
        ).where(
            and_(
                Charge.user_id == user_id,
                Charge.created_at >= datetime.combine(start_date, datetime.min.time()),
                Charge.created_at < datetime.combine(end_date, datetime.min.time()),
            )
        )

        result = await self.db.execute(query)
        row = result.one()

        month_names = [
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
        ]
        month_name = month_names[month - 1] if 1 <= month <= 12 else str(month)

        total_paid = float(row.total_paid)
        total_pending = float(row.total_pending)
        total_overdue = float(row.total_overdue)
        total_cancelled = float(row.total_cancelled)

        message = f"📊 *Resumo financeiro — {month_name}/{year}:*\n\n"
        message += f"💰 Pagas: R$ {total_paid:.2f}\n"
        message += f"⏳ Pendentes: R$ {total_pending:.2f}\n"
        message += f"⚠️ Vencidas: R$ {total_overdue:.2f}\n"
        message += f"❌ Canceladas: R$ {total_cancelled:.2f}\n"

        if total_paid > 0:
            message += f"\nEm {month_name}, você recebeu R$ {total_paid:.2f} em cobranças pagas."

        return message

    async def top_overdue_customers(self, user_id: int, limit: int = 5) -> str:
        """List customers with most overdue charges."""
        charges = await self.charge_repo.get_overdue_by_user(user_id)
        if not charges:
            return "✅ Nenhum cliente com cobranças vencidas."

        customer_totals: Dict[str, float] = {}
        for c in charges:
            name = c.customer_name
            customer_totals[name] = customer_totals.get(name, 0) + float(c.amount)

        sorted_customers = sorted(customer_totals.items(), key=lambda x: x[1], reverse=True)[:limit]

        message = f"⚠️ *Clientes com mais atrasos:*\n\n"
        for i, (name, total) in enumerate(sorted_customers, 1):
            message += f"{i}. {name} — R$ {total:.2f}\n"

        return message
