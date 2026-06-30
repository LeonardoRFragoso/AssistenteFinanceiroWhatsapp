from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any
from app.models.pending_action import PendingAction, PendingActionStatus
from app.models.charge import Charge
from app.repositories.pending_action_repository import PendingActionRepository
from app.services.charge_service import ChargeService
from app.schemas.charge import ChargeCreate
from app.core.logging import logger


class PendingActionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.action_repo = PendingActionRepository(db)
        self.charge_service = ChargeService(db)

    async def create_charge_action(
        self,
        user_id: int,
        amount: float,
        customer_name: str,
        description: Optional[str] = None,
        customer_phone: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> PendingAction:
        """Create a pending action for charge creation."""
        await self.action_repo.expire_old_actions(datetime.utcnow())

        payload = {
            "amount": amount,
            "customer_name": customer_name,
            "description": description,
            "customer_phone": customer_phone,
            "due_date": due_date
        }

        expires_at = datetime.utcnow() + timedelta(minutes=10)
        action = await self.action_repo.create(
            user_id=user_id,
            action_type="create_charge",
            payload=payload,
            expires_at=expires_at
        )

        logger.info(f"Pending charge action {action.id} created for user {user_id}")
        return action

    async def get_pending_action(self, user_id: int, action_type: Optional[str] = None) -> Optional[PendingAction]:
        await self.action_repo.expire_old_actions(datetime.utcnow())
        return await self.action_repo.get_latest_pending_by_user(user_id, action_type)

    async def confirm_and_execute(self, action_id: int, user_id: int) -> Optional[Charge]:
        """Confirm a pending action and execute the charge creation."""
        action = await self.action_repo.get_by_id(action_id, user_id)
        if not action or action.status != PendingActionStatus.PENDING:
            return None

        await self.action_repo.confirm(action_id)

        payload = action.payload
        try:
            amount = Decimal(str(payload.get("amount", 0)))
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")

            charge_data = ChargeCreate(
                customer_name=payload.get("customer_name", "Cliente"),
                customer_phone=payload.get("customer_phone"),
                amount=amount,
                description=payload.get("description"),
                due_date=payload.get("due_date")
            )

            charge = await self.charge_service.create_charge(user_id, charge_data)
            await self.action_repo.mark_executed(action_id)
            return charge
        except (InvalidOperation, ValueError) as e:
            logger.error(f"Invalid amount in pending action {action_id}: {str(e)}")
            await self.action_repo.mark_failed(action_id)
            return None
        except Exception as e:
            logger.error(f"Error executing pending action {action_id}: {str(e)}")
            await self.action_repo.mark_failed(action_id)
            return None

    async def cancel_action(self, action_id: int, user_id: int) -> Optional[PendingAction]:
        return await self.action_repo.cancel(action_id)

    async def cancel_latest_pending(self, user_id: int, action_type: Optional[str] = None) -> Optional[PendingAction]:
        action = await self.get_pending_action(user_id, action_type)
        if not action:
            return None
        return await self.action_repo.cancel(action.id)

    def format_charge_summary(self, action: PendingAction) -> str:
        """Format a friendly confirmation message from a pending charge action."""
        payload = action.payload
        amount = payload.get("amount", 0)
        customer = payload.get("customer_name", "Cliente")
        description = payload.get("description", "")

        message = (
            f"💰 *Cobrança de R$ {float(amount):.2f}*\n"
            f"👤 Cliente: {customer}\n"
        )
        if description:
            message += f"📝 Referente a: {description}\n"
        message += "\nDeseja confirmar e gerar o link de pagamento?\nResponda *sim* ou *confirmo*."
        return message
