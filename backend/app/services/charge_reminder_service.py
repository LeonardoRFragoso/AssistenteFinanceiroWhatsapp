from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import List, Dict, Any
from app.models.charge import Charge
from app.models.charge_reminder_log import ReminderType
from app.repositories.charge_repository import ChargeRepository
from app.repositories.charge_reminder_log_repository import ChargeReminderLogRepository
from app.repositories.user_repository import UserRepository
from app.integrations.twilio_whatsapp import TwilioWhatsAppService
from app.core.config import settings
from app.core.logging import logger


class ChargeReminderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self.reminder_repo = ChargeReminderLogRepository(db)
        self.user_repo = UserRepository(db)

    async def run_reminders(self) -> Dict[str, Any]:
        """Find charges needing reminders and send WhatsApp notifications.

        Returns a summary of reminders sent and skipped.
        """
        sent_due_soon = 0
        sent_overdue = 0
        skipped = 0
        errors = 0

        due_soon_charges = await self.charge_repo.get_all_due_soon(days_ahead=1)
        for charge in due_soon_charges:
            if await self.reminder_repo.was_reminded_today(charge.id, ReminderType.DUE_SOON):
                skipped += 1
                continue
            try:
                await self._send_reminder(charge, ReminderType.DUE_SOON)
                sent_due_soon += 1
            except Exception as e:
                logger.error(f"Error sending due_soon reminder for charge {charge.id}: {str(e)}")
                errors += 1

        overdue_charges = await self.charge_repo.get_all_overdue()
        for charge in overdue_charges:
            if await self.reminder_repo.was_reminded_today(charge.id, ReminderType.OVERDUE):
                skipped += 1
                continue
            try:
                await self._send_reminder(charge, ReminderType.OVERDUE)
                sent_overdue += 1
            except Exception as e:
                logger.error(f"Error sending overdue reminder for charge {charge.id}: {str(e)}")
                errors += 1

        return {
            "sent_due_soon": sent_due_soon,
            "sent_overdue": sent_overdue,
            "skipped": skipped,
            "errors": errors,
            "total_processed": sent_due_soon + sent_overdue + skipped + errors
        }

    async def _send_reminder(self, charge: Charge, reminder_type: ReminderType) -> None:
        """Send a WhatsApp reminder for a charge and log it."""
        user = await self.user_repo.get_by_id(charge.user_id)
        if not user or not user.phone_number:
            logger.info(f"No phone number for user {charge.user_id}, skipping reminder for charge {charge.id}")
            await self.reminder_repo.create(charge.id, charge.user_id, reminder_type)
            return

        message = self._format_reminder_message(charge, reminder_type)

        try:
            twilio = TwilioWhatsAppService()
            await twilio.send_message(user.phone_number, message)
        except Exception as e:
            logger.warning(f"Could not send WhatsApp reminder (Twilio not configured?): {str(e)}")

        await self.reminder_repo.create(charge.id, charge.user_id, reminder_type)
        logger.info(f"Reminder ({reminder_type.value}) sent for charge {charge.id} to user {charge.user_id}")

    def _format_reminder_message(self, charge: Charge, reminder_type: ReminderType) -> str:
        amount_str = f"R$ {float(charge.amount):.2f}"
        customer = charge.customer_name

        if reminder_type == ReminderType.DUE_SOON:
            due_str = charge.due_date.strftime("%d/%m/%Y") if charge.due_date else "em breve"
            return (
                f"⏰ *Lembrete de cobrança*\n\n"
                f"A cobrança de *{amount_str}* para *{customer}* vence em *{due_str}*.\n"
                f"🔗 Link: {charge.payment_link or 'não disponível'}"
            )
        elif reminder_type == ReminderType.OVERDUE:
            due_str = charge.due_date.strftime("%d/%m/%Y") if charge.due_date else "data não definida"
            return (
                f"⚠️ *Cobrança vencida*\n\n"
                f"A cobrança de *{amount_str}* para *{customer}* está vencida desde *{due_str}*.\n"
                f"🔗 Link: {charge.payment_link or 'não disponível'}"
            )
        return ""
