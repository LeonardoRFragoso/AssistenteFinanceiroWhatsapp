from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.reminder import Reminder
from app.models.subscription import Subscription
from app.utils.dependencies import get_current_admin_user
from app.core.logging import logger
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/admin", tags=["Admin CRUD"])


# ============= SCHEMAS =============

class UserListResponse(BaseModel):
    id: int
    name: str
    email: str
    phone_number: str
    created_at: datetime
    plan: Optional[str] = None
    transactions_count: int = 0
    
    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None


class TransactionListResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    type: str
    amount: float
    category: str
    description: Optional[str]
    payment_method: str
    date: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ReminderListResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    title: str
    description: Optional[str]
    due_date: datetime
    is_completed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============= USERS CRUD =============

@router.get("/users", response_model=List[UserListResponse])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all users with pagination and search"""
    try:
        query = select(User)
        
        if search:
            query = query.where(
                or_(
                    User.name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    User.phone_number.ilike(f"%{search}%")
                )
            )
        
        query = query.order_by(desc(User.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()
        
        # Enrich with subscription and transaction data
        response = []
        for user in users:
            # Get subscription
            sub_result = await db.execute(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            subscription = sub_result.scalar_one_or_none()
            
            # Count transactions
            trans_result = await db.execute(
                select(func.count(Transaction.id)).where(Transaction.user_id == user.id)
            )
            trans_count = trans_result.scalar_one()
            
            response.append(UserListResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                phone_number=user.phone_number,
                created_at=user.created_at,
                plan=subscription.plan if subscription else "free",
                transactions_count=trans_count
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving users"
        )


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get detailed user information"""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user detail: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user"
        )


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update user information"""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if data.name is not None:
            user.name = data.name
        if data.email is not None:
            user.email = data.email
        if data.phone_number is not None:
            user.phone_number = data.phone_number
        
        await db.commit()
        await db.refresh(user)
        
        return {"message": "User updated successfully", "user": user}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a user and all related data"""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete user (cascade will handle related data)
        await db.delete(user)
        await db.commit()
        
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting user"
        )


# ============= TRANSACTIONS CRUD =============

@router.get("/transactions", response_model=List[TransactionListResponse])
async def get_all_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[int] = None,
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all transactions with filters"""
    try:
        query = select(Transaction, User).join(User, Transaction.user_id == User.id)
        
        if user_id:
            query = query.where(Transaction.user_id == user_id)
        if type:
            query = query.where(Transaction.type == type)
        
        query = query.order_by(desc(Transaction.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        rows = result.all()
        
        response = []
        for transaction, user in rows:
            response.append(TransactionListResponse(
                id=transaction.id,
                user_id=transaction.user_id,
                user_name=user.name,
                type=transaction.type,
                amount=float(transaction.amount),
                category=transaction.category,
                description=transaction.description,
                payment_method=transaction.payment_method,
                date=transaction.date.isoformat(),
                created_at=transaction.created_at
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting transactions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving transactions"
        )


@router.delete("/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a transaction"""
    try:
        result = await db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        await db.delete(transaction)
        await db.commit()
        
        return {"message": "Transaction deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting transaction: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting transaction"
        )


# ============= REMINDERS CRUD =============

@router.get("/reminders", response_model=List[ReminderListResponse])
async def get_all_reminders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[int] = None,
    completed: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all reminders with filters"""
    try:
        query = select(Reminder, User).join(User, Reminder.user_id == User.id)
        
        if user_id:
            query = query.where(Reminder.user_id == user_id)
        if completed is not None:
            query = query.where(Reminder.is_completed == completed)
        
        query = query.order_by(desc(Reminder.due_date)).offset(skip).limit(limit)
        result = await db.execute(query)
        rows = result.all()
        
        response = []
        for reminder, user in rows:
            response.append(ReminderListResponse(
                id=reminder.id,
                user_id=reminder.user_id,
                user_name=user.name,
                title=reminder.title,
                description=reminder.description,
                due_date=reminder.due_date,
                is_completed=reminder.is_completed,
                created_at=reminder.created_at
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting reminders: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving reminders"
        )


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(
    reminder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a reminder"""
    try:
        result = await db.execute(
            select(Reminder).where(Reminder.id == reminder_id)
        )
        reminder = result.scalar_one_or_none()
        
        if not reminder:
            raise HTTPException(status_code=404, detail="Reminder not found")
        
        await db.delete(reminder)
        await db.commit()
        
        return {"message": "Reminder deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting reminder: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting reminder"
        )


@router.patch("/users/{user_id}/phone")
async def update_user_phone(
    user_id: int,
    phone_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update user phone number"""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        old_phone = user.phone_number
        user.phone_number = phone_number
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Updated phone for user {user_id}: {old_phone} -> {phone_number}")
        
        return {
            "message": "Phone number updated successfully",
            "user_id": user.id,
            "email": user.email,
            "old_phone": old_phone,
            "new_phone": user.phone_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating user phone: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating phone number"
        )


# ============= STATISTICS =============

@router.get("/stats/overview")
async def get_overview_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get overview statistics"""
    try:
        # Total users
        total_users = await db.execute(select(func.count(User.id)))
        
        # Active users (users with active subscriptions)
        active_users = await db.execute(
            select(func.count(Subscription.user_id)).where(Subscription.status == "active")
        )
        
        # Total transactions
        total_transactions = await db.execute(select(func.count(Transaction.id)))
        
        # Total reminders
        total_reminders = await db.execute(select(func.count(Reminder.id)))
        
        # Active subscriptions
        active_subs = await db.execute(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        )
        
        return {
            "total_users": total_users.scalar_one(),
            "active_users": active_users.scalar_one(),
            "total_transactions": total_transactions.scalar_one(),
            "total_reminders": total_reminders.scalar_one(),
            "active_subscriptions": active_subs.scalar_one()
        }
        
    except Exception as e:
        logger.error(f"Error getting overview stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving statistics"
        )
