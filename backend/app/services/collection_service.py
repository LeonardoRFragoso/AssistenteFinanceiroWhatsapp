from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timezone
from decimal import Decimal
from app.models.charge import Charge, ChargeStatus
from app.models.customer import Customer
from app.models.collection_rule import CollectionRule, TriggerType
from app.models.collection_message_log import CollectionMessageLog, CollectionMessageStatus
from app.models.message_template import MessageTemplate, MessageTone
from app.services.customer_service import CustomerService
from app.services.message_template_service import MessageTemplateService
from app.schemas.collection_rule import CollectionRuleCreate
from app.core.logging import logger


class CollectionService:
    """Service for managing collection rules and generating follow-up messages.

    This service NEVER sends messages automatically. It only generates
    drafts and previews. Sending requires explicit user confirmation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_rule(self, user_id: int, data: CollectionRuleCreate, organization_id: Optional[int] = None) -> CollectionRule:
        if data.template_id:
            mt_service = MessageTemplateService(self.db)
            template = await mt_service.get_template(data.template_id, user_id, organization_id)
            if not template:
                raise ValueError("Template not found")

        rule = CollectionRule(
            user_id=user_id,
            organization_id=organization_id,
            name=data.name,
            days_offset=data.days_offset,
            trigger_type=data.trigger_type,
            template_id=data.template_id,
            active=True,
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        logger.info(f"Collection rule {rule.id} created for user {user_id}")
        return rule

    async def list_rules(self, user_id: int, organization_id: Optional[int] = None) -> List[CollectionRule]:
        query = select(CollectionRule).where(
            and_(CollectionRule.user_id == user_id, CollectionRule.active == True)
        )
        if organization_id is not None:
            query = query.where(CollectionRule.organization_id == organization_id)
        result = await self.db.execute(
            query.order_by(CollectionRule.days_offset.asc())
        )
        return list(result.scalars().all())

    async def deactivate_rule(self, rule_id: int, user_id: int, organization_id: Optional[int] = None) -> Optional[CollectionRule]:
        query = select(CollectionRule).where(
            and_(CollectionRule.id == rule_id, CollectionRule.user_id == user_id)
        )
        if organization_id is not None:
            query = query.where(CollectionRule.organization_id == organization_id)
        result = await self.db.execute(query)
        rule = result.scalar_one_or_none()
        if not rule:
            return None
        rule.active = False
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def get_overdue_charges(self, user_id: int, organization_id: Optional[int] = None) -> List[Charge]:
        """Get all overdue charges for a user."""
        today = date.today()
        query = select(Charge).where(
            and_(
                Charge.user_id == user_id,
                Charge.status == ChargeStatus.PENDING,
                Charge.due_date < today,
            )
        )
        if organization_id is not None:
            query = query.where(Charge.organization_id == organization_id)
        result = await self.db.execute(
            query.order_by(Charge.due_date.asc())
        )
        return list(result.scalars().all())

    async def generate_followup_previews(
        self,
        user_id: int,
        limit: int = 10,
        organization_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate draft follow-up messages for overdue charges.

        Does NOT send any messages. Returns previews only.
        """
        overdue = await self.get_overdue_charges(user_id, organization_id)
        overdue = overdue[:limit]

        today = date.today()
        mt_service = MessageTemplateService(self.db)
        customer_service = CustomerService(self.db)

        templates = await mt_service.list_templates(user_id, active_only=True, organization_id=organization_id)
        firm_template = next(
            (t for t in templates if t.tone == MessageTone.FIRM),
            templates[0] if templates else None,
        )

        items = []
        for charge in overdue:
            customer = await customer_service.get_or_create_customer(
                user_id, charge.customer_name, charge.customer_phone, organization_id=organization_id
            )

            days_overdue = (today - charge.due_date).days if charge.due_date else 0

            if firm_template:
                context = {
                    "customer_name": charge.customer_name,
                    "amount": f"{float(charge.amount):.2f}",
                    "description": charge.description or "cobrança",
                    "due_date": charge.due_date.strftime("%d/%m/%Y") if charge.due_date else "",
                    "payment_link": charge.payment_link or "",
                    "qr_code_note": "Sandbox/Demo — não representa Pix real",
                    "company_name": "PayFlow AI",
                }
                rendered = mt_service.render_template(firm_template.template_text, context)
                template_name = firm_template.name
            else:
                rendered = (
                    f"Olá, {charge.customer_name}!\n\n"
                    f"A cobrança de R$ {float(charge.amount):.2f} referente a "
                    f"{charge.description or 'cobrança'} está em atraso "
                    f"(vencimento: {charge.due_date.strftime('%d/%m/%Y') if charge.due_date else 'N/A'}).\n\n"
                    f"Link de pagamento: {charge.payment_link or 'N/A'}\n\n"
                    f"Por favor, regularize o pagamento."
                )
                template_name = None

            items.append({
                "charge_id": charge.id,
                "customer_name": charge.customer_name,
                "amount": float(charge.amount),
                "due_date": charge.due_date.isoformat() if charge.due_date else None,
                "days_overdue": days_overdue,
                "rendered_message": rendered,
                "template_name": template_name,
            })

        return {
            "items": items,
            "total": len(items),
            "message": (
                f"Encontrei {len(items)} cobrança(s) vencida(s). "
                "Deseja gerar os rascunhos? Responda \"sim\" para preparar ou \"não\" para cancelar."
                if items else "Nenhuma cobrança vencida encontrada."
            ),
        }

    async def log_message(
        self,
        user_id: int,
        charge_id: int,
        customer_id: Optional[int],
        template_id: Optional[int],
        message_preview: str,
        status: CollectionMessageStatus = CollectionMessageStatus.DRAFT,
        organization_id: Optional[int] = None,
    ) -> CollectionMessageLog:
        """Create a log entry for a collection message."""
        log = CollectionMessageLog(
            user_id=user_id,
            organization_id=organization_id,
            charge_id=charge_id,
            customer_id=customer_id,
            template_id=template_id,
            channel="whatsapp",
            message_preview=message_preview[:500],
            status=status,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def already_sent_today(self, user_id: int, charge_id: int, organization_id: Optional[int] = None) -> bool:
        """Check if a follow-up was already sent/logged for this charge today."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        query = select(func.count()).select_from(CollectionMessageLog).where(
            and_(
                CollectionMessageLog.user_id == user_id,
                CollectionMessageLog.charge_id == charge_id,
                CollectionMessageLog.created_at >= today_start,
                CollectionMessageLog.status.in_([
                    CollectionMessageStatus.DRAFT,
                    CollectionMessageStatus.PENDING_CONFIRMATION,
                    CollectionMessageStatus.SENT,
                ]),
            )
        )
        if organization_id is not None:
            query = query.where(CollectionMessageLog.organization_id == organization_id)
        result = await self.db.execute(query)
        count = result.scalar() or 0
        return count > 0

    async def list_logs(self, user_id: int, limit: int = 20, organization_id: Optional[int] = None) -> List[CollectionMessageLog]:
        query = select(CollectionMessageLog).where(CollectionMessageLog.user_id == user_id)
        if organization_id is not None:
            query = query.where(CollectionMessageLog.organization_id == organization_id)
        result = await self.db.execute(
            query.order_by(CollectionMessageLog.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
