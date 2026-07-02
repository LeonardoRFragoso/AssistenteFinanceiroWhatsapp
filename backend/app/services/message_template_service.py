from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional, Dict, Any
import re
from app.models.message_template import MessageTemplate, MessageTone
from app.schemas.message_template import (
    MessageTemplateCreate,
    MessageTemplateUpdate,
    ALLOWED_PLACEHOLDERS,
    AGGRESSIVE_WORDS,
)
from app.core.logging import logger


class MessageTemplateService:
    """Service for managing message templates and rendering them safely."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_templates(self, user_id: int, active_only: bool = False) -> List[MessageTemplate]:
        query = select(MessageTemplate).where(MessageTemplate.user_id == user_id)
        if active_only:
            query = query.where(MessageTemplate.active == True)
        query = query.order_by(MessageTemplate.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_template(self, user_id: int, data: MessageTemplateCreate) -> MessageTemplate:
        self._validate_placeholders(data.template_text)
        template = MessageTemplate(
            user_id=user_id,
            name=data.name,
            tone=data.tone,
            template_text=data.template_text,
            active=True,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        logger.info(f"Message template {template.id} created for user {user_id}")
        return template

    async def update_template(self, template_id: int, user_id: int, data: MessageTemplateUpdate) -> Optional[MessageTemplate]:
        template = await self._get_template(template_id, user_id)
        if not template:
            return None
        if data.name is not None:
            template.name = data.name
        if data.tone is not None:
            template.tone = data.tone
        if data.template_text is not None:
            self._validate_placeholders(data.template_text)
            template.template_text = data.template_text
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def deactivate_template(self, template_id: int, user_id: int) -> Optional[MessageTemplate]:
        template = await self._get_template(template_id, user_id)
        if not template:
            return None
        template.active = False
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def get_template(self, template_id: int, user_id: int) -> Optional[MessageTemplate]:
        return await self._get_template(template_id, user_id)

    def render_template(self, template_text: str, context: Dict[str, Any]) -> str:
        """Render a template with safe placeholder substitution.

        Only allowed placeholders are substituted. Unknown placeholders
        are left as-is (not removed) to make them visible to the user.
        """
        rendered = template_text
        for placeholder in ALLOWED_PLACEHOLDERS:
            key = placeholder.strip("{}")
            value = context.get(key, "")
            if value is None:
                value = ""
            rendered = rendered.replace(placeholder, str(value))
        return rendered

    def preview_template(self, template: MessageTemplate, context: Dict[str, Any]) -> str:
        """Render a template with preview context."""
        return self.render_template(template.template_text, context)

    def _validate_placeholders(self, text: str) -> None:
        """Validate that only allowed placeholders are used in the template."""
        found_placeholders = set(re.findall(r'\{[^}]+\}', text))
        unknown = found_placeholders - ALLOWED_PLACEHOLDERS
        if unknown:
            raise ValueError(
                f"Unknown placeholders: {', '.join(sorted(unknown))}. "
                f"Allowed: {', '.join(sorted(ALLOWED_PLACEHOLDERS))}"
            )

    async def _get_template(self, template_id: int, user_id: int) -> Optional[MessageTemplate]:
        result = await self.db.execute(
            select(MessageTemplate).where(
                and_(MessageTemplate.id == template_id, MessageTemplate.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def seed_default_templates(self, user_id: int) -> None:
        """Create default templates for a new user if they have none."""
        existing = await self.list_templates(user_id)
        if existing:
            return

        defaults = [
            MessageTemplateCreate(
                name="Lembrete amigável (antes do vencimento)",
                tone=MessageTone.FRIENDLY,
                template_text=(
                    "Olá, {customer_name}! Tudo bem?\n\n"
                    "Passando para lembrar da cobrança de R$ {amount}, "
                    "referente a {description}, com vencimento em {due_date}.\n\n"
                    "Segue o link para pagamento:\n{payment_link}\n\n"
                    "Qualquer dúvida, estou à disposição! 😊"
                ),
            ),
            MessageTemplateCreate(
                name="Cobrança neutra (no vencimento)",
                tone=MessageTone.NEUTRAL,
                template_text=(
                    "Olá, {customer_name}!\n\n"
                    "Este é um lembrete de que a cobrança de R$ {amount} "
                    "referente a {description} vence hoje ({due_date}).\n\n"
                    "Link de pagamento: {payment_link}\n\n"
                    "Obrigado!"
                ),
            ),
            MessageTemplateCreate(
                name="Cobrança firme (após vencimento)",
                tone=MessageTone.FIRM,
                template_text=(
                    "Olá, {customer_name}.\n\n"
                    "A cobrança de R$ {amount} referente a {description} "
                    "está com o vencimento em atraso ({due_date}).\n\n"
                    "Por favor, regularize o pagamento através do link:\n{payment_link}\n\n"
                    "Em caso de dúvidas, entre em contato."
                ),
            ),
            MessageTemplateCreate(
                name="Agradecimento (após pagamento)",
                tone=MessageTone.FRIENDLY,
                template_text=(
                    "Olá, {customer_name}!\n\n"
                    "Recebemos o pagamento de R$ {amount} referente a {description}. "
                    "Muito obrigado pela pontualidade! 🎉\n\n"
                    "Qualquer coisa, estamos à disposição."
                ),
            ),
        ]

        for tmpl in defaults:
            await self.create_template(user_id, tmpl)

        logger.info(f"Seeded {len(defaults)} default templates for user {user_id}")
