from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from app.models.charge import Charge, ChargeStatus
from app.models.provider_event import ProviderEvent
from app.repositories.charge_repository import ChargeRepository
from app.repositories.provider_event_repository import ProviderEventRepository
from app.repositories.user_repository import UserRepository
from app.providers.provider_factory import get_payment_provider
from app.schemas.charge import ChargeCreate, ChargeSummaryResponse
from app.core.logging import logger
from app.integrations.twilio_whatsapp import TwilioWhatsAppService


class ChargeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self.event_repo = ProviderEventRepository(db)
        self.user_repo = UserRepository(db)
        self.provider = get_payment_provider()

    async def create_charge(self, user_id: int, data: ChargeCreate) -> Charge:
        """Create a charge with the configured provider and persist it."""
        provider_name = data.provider or self.provider.name

        # If provider is explicit, fetch that provider instance for this call only.
        provider = self.provider
        if provider_name != self.provider.name:
            from app.providers.provider_factory import get_payment_provider
            provider = get_payment_provider(provider_name)

        external_reference = f"payflow_user_{user_id}"
        due_date_str = data.due_date.isoformat() if data.due_date else None

        user = await self.user_repo.get_by_id(user_id)
        payer_email = user.email if user else "payer@example.com"

        result = await provider.create_charge(
            amount=data.amount,
            description=data.description or f"Cobrança para {data.customer_name}",
            customer_name=data.customer_name,
            customer_phone=data.customer_phone,
            external_reference=external_reference,
            due_date=due_date_str,
            payer_email=payer_email
        )

        charge = await self.charge_repo.create(
            user_id=user_id,
            customer_name=data.customer_name,
            amount=Decimal(str(result["amount"])) if result.get("amount") else data.amount,
            provider=provider_name,
            provider_charge_id=result.get("provider_charge_id"),
            payment_link=result.get("payment_link"),
            qr_code=result.get("qr_code"),
            qr_code_base64=result.get("qr_code_base64"),
            description=data.description,
            customer_phone=data.customer_phone,
            due_date=data.due_date,
            status=ChargeStatus.PENDING
        )

        logger.info(f"Charge {charge.id} created for user {user_id} via {provider_name}")
        return charge

    async def get_user_charges(self, user_id: int, limit: int = 50, status: Optional[str] = None) -> List[Charge]:
        return await self.charge_repo.get_by_user(user_id, limit=limit, status=status)

    async def get_charges_paginated(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> dict:
        """Return paginated charges with total count and pagination metadata."""
        charges, total = await self.charge_repo.get_paginated(
            user_id=user_id,
            page=page,
            page_size=page_size,
            status=status,
            search=search,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return {
            "items": charges,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def get_charge(self, charge_id: int, user_id: Optional[int] = None) -> Optional[Charge]:
        return await self.charge_repo.get_by_id(charge_id, user_id)

    async def cancel_charge(self, charge_id: int, user_id: int) -> Optional[Charge]:
        return await self.charge_repo.cancel(charge_id, user_id)

    def get_derived_status(self, charge: Charge) -> str:
        """Return the effective status of a charge, considering overdue."""
        if charge.status == ChargeStatus.PENDING and charge.due_date:
            if charge.due_date < date.today():
                return "overdue"
        return charge.status.value

    async def get_summary(self, user_id: int) -> ChargeSummaryResponse:
        """Get charge summary statistics for a user."""
        data = await self.charge_repo.get_summary(user_id)
        return ChargeSummaryResponse(**data)

    async def get_pending_charges(self, user_id: int) -> List[Charge]:
        return await self.charge_repo.get_pending_by_user(user_id)

    async def get_paid_charges(self, user_id: int, limit: int = 10) -> List[Charge]:
        return await self.charge_repo.get_paid_by_user(user_id, limit=limit)

    async def get_overdue_charges(self, user_id: int) -> List[Charge]:
        return await self.charge_repo.get_overdue_by_user(user_id)

    async def find_charges_by_customer_name(self, user_id: int, name: str) -> List[Charge]:
        return await self.charge_repo.find_by_customer_name(user_id, name)

    async def find_charges_by_amount(self, user_id: int, amount: Decimal) -> List[Charge]:
        return await self.charge_repo.find_by_amount(user_id, amount)

    async def get_latest_charge(self, user_id: int) -> Optional[Charge]:
        charges = await self.charge_repo.get_by_user(user_id, limit=1)
        return charges[0] if charges else None

    async def process_payment_event(
        self,
        provider: str,
        event_type: str,
        provider_charge_id: str,
        external_reference: Optional[str],
        amount: Optional[Decimal],
        status: Optional[str],
        paid_at: Optional[datetime],
        raw_payload: Dict[str, Any]
    ) -> Optional[Charge]:
        """Persist provider event and update the charge if it exists."""
        await self.event_repo.create(
            provider=provider,
            event_type=event_type,
            payload=raw_payload,
            external_id=provider_charge_id
        )

        charge = await self.charge_repo.get_by_provider_charge_id(provider_charge_id)
        if not charge:
            logger.warning(f"Provider event received for unknown charge: {provider_charge_id}")
            return None

        if charge.status == ChargeStatus.PAID:
            logger.info(f"Charge {charge.id} already paid, ignoring duplicate event")
            return charge

        if status == "paid" or status == "approved":
            charge.status = ChargeStatus.PAID
            charge.paid_at = paid_at or datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(charge)
            logger.info(f"Charge {charge.id} marked as paid via {provider}")
            await self._notify_payment_received(charge)

        return charge

    async def process_webhook_payload(self, provider_name: str, payload: Dict[str, Any]) -> Optional[Charge]:
        """Parse a provider webhook payload and process the resulting event."""
        from app.providers.provider_factory import get_payment_provider
        provider = get_payment_provider(provider_name)
        event = provider.parse_webhook_event(payload)
        if not event:
            logger.warning(f"Could not parse webhook payload from {provider_name}")
            return None

        paid_at = event.get("paid_at")
        if isinstance(paid_at, str):
            try:
                paid_at = datetime.fromisoformat(paid_at)
            except ValueError:
                paid_at = None

        return await self.process_payment_event(
            provider=provider_name,
            event_type=event["event_type"],
            provider_charge_id=event["provider_charge_id"],
            external_reference=event.get("external_reference"),
            amount=event.get("amount"),
            status=event.get("status"),
            paid_at=paid_at,
            raw_payload=event.get("raw_data", payload)
        )

    async def _notify_payment_received(self, charge: Charge) -> None:
        """Send a WhatsApp notification to the user when a charge is paid."""
        try:
            user = await self.user_repo.get_by_id(charge.user_id)
            if not user or not user.phone_number:
                return

            twilio = TwilioWhatsAppService()
            message = (
                f"✅ *Pagamento recebido!*\n\n"
                f"{charge.customer_name} pagou *R$ {float(charge.amount):.2f}*"
            )
            if charge.description:
                message += f" referente a *{charge.description}*"
            message += ".\n\nObrigado por usar o PayFlow AI! 🎉"

            await twilio.send_message(user.phone_number, message)
        except Exception as e:
            logger.error(f"Error notifying payment received: {str(e)}")
