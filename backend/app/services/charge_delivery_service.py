from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from app.models.charge import Charge
from app.models.charge_delivery_log import DeliveryStatus, DeliveryChannel
from app.repositories.charge_delivery_log_repository import ChargeDeliveryLogRepository
from app.integrations.twilio_whatsapp import TwilioWhatsAppService
from app.core.config import settings
from app.core.logging import logger


class ChargeDeliveryService:
    """Send charge payment links to customers via WhatsApp with logging."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.delivery_repo = ChargeDeliveryLogRepository(db)

    async def send_charge_link_to_customer(
        self,
        charge: Charge,
        user_id: int
    ) -> Dict[str, Any]:
        """Send a payment link to the charge's customer via WhatsApp.

        Returns a dict with status and message. If Twilio is not configured,
        the send is simulated and logged as SIMULATED.
        """
        customer_phone = charge.customer_phone
        if not customer_phone:
            return {
                "success": False,
                "message": "Cliente não possui telefone cadastrado."
            }

        message = self._format_customer_message(charge)

        # Check if Twilio is configured
        twilio_configured = (
            settings.TWILIO_ACCOUNT_SID
            and settings.TWILIO_AUTH_TOKEN
            and settings.TWILIO_WHATSAPP_NUMBER
        )

        if not twilio_configured:
            logger.info(
                f"Twilio not configured — simulating delivery for charge {charge.id} "
                f"to {customer_phone}"
            )
            await self.delivery_repo.create(
                charge_id=charge.id,
                user_id=user_id,
                customer_phone=customer_phone,
                channel=DeliveryChannel.WHATSAPP,
                status=DeliveryStatus.SIMULATED,
                error_message=None
            )
            return {
                "success": True,
                "simulated": True,
                "message": f"Link simulado para {customer_phone} (Twilio não configurado)."
            }

        try:
            twilio = TwilioWhatsAppService()
            await twilio.send_message(customer_phone, message)
            await self.delivery_repo.create(
                charge_id=charge.id,
                user_id=user_id,
                customer_phone=customer_phone,
                channel=DeliveryChannel.WHATSAPP,
                status=DeliveryStatus.SENT,
                error_message=None
            )
            logger.info(f"Charge link sent to customer for charge {charge.id}")
            return {
                "success": True,
                "simulated": False,
                "message": f"Link enviado para {customer_phone}."
            }
        except Exception as e:
            logger.error(f"Error sending charge link to customer: {str(e)}")
            await self.delivery_repo.create(
                charge_id=charge.id,
                user_id=user_id,
                customer_phone=customer_phone,
                channel=DeliveryChannel.WHATSAPP,
                status=DeliveryStatus.FAILED,
                error_message=str(e)
            )
            return {
                "success": False,
                "simulated": False,
                "message": f"Erro ao enviar: {str(e)}"
            }

    def _format_customer_message(self, charge: Charge) -> str:
        amount_str = f"R$ {float(charge.amount):.2f}"
        desc = charge.description or "cobrança"
        link = charge.payment_link or "não disponível"
        return (
            f"Olá, {charge.customer_name}. "
            f"Você recebeu uma cobrança de {amount_str} referente a {desc}.\n\n"
            f"Link de pagamento:\n{link}"
        )
