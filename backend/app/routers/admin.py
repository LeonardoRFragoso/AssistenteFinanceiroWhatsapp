from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from datetime import datetime, timedelta, date
from decimal import Decimal
from app.core.database import get_db
from app.schemas.metrics import MetricsResponse
from app.schemas.analytics import (
    FunnelMetrics, 
    CohortMetrics, 
    DashboardMetrics,
    ConversionMetrics,
    RetentionMetrics,
    ChurnMetrics,
    LTVMetrics
)
from app.services.analytics_service import AnalyticsService
from app.models.user import User
from app.models.subscription import Subscription
from app.models.transaction import Transaction, TransactionType
from app.models.payment_event import PaymentEvent
from app.core.logging import logger
from app.utils.dependencies import get_current_admin_user
import re

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/metrics", response_model=MetricsResponse)
async def get_admin_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    try:
        total_users_result = await db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar_one()
        
        active_users_result = await db.execute(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        )
        active_users = active_users_result.scalar_one()
        
        inactive_users = total_users - active_users
        
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        
        mrr_result = await db.execute(
            select(func.count(Subscription.id))
            .where(Subscription.status == "active")
        )
        active_subscriptions = mrr_result.scalar_one()
        
        mrr = Decimal(active_subscriptions * 29.90)
        
        total_revenue_result = await db.execute(
            select(func.coalesce(func.sum(PaymentEvent.amount), 0))
            .where(
                and_(
                    PaymentEvent.status == "approved",
                    PaymentEvent.amount.isnot(None)
                )
            )
        )
        total_revenue = total_revenue_result.scalar_one()
        
        transactions_count_result = await db.execute(
            select(func.count(Transaction.id))
        )
        transactions_count = transactions_count_result.scalar_one()
        
        avg_transaction_result = await db.execute(
            select(func.avg(Transaction.amount))
        )
        avg_transaction_value = avg_transaction_result.scalar_one() or Decimal(0)
        
        last_month = month_start - timedelta(days=1)
        last_month_start = datetime(last_month.year, last_month.month, 1)
        
        last_month_active_result = await db.execute(
            select(func.count(Subscription.id))
            .where(
                and_(
                    Subscription.status == "active",
                    Subscription.created_at < month_start
                )
            )
        )
        last_month_active = last_month_active_result.scalar_one()
        
        churned_result = await db.execute(
            select(func.count(Subscription.id))
            .where(
                and_(
                    Subscription.status == "inactive",
                    Subscription.updated_at >= last_month_start,
                    Subscription.updated_at < month_start
                )
            )
        )
        churned = churned_result.scalar_one()
        
        churn_rate = (churned / last_month_active * 100) if last_month_active > 0 else 0.0
        
        users_by_plan_result = await db.execute(
            select(Subscription.plan, func.count(Subscription.id))
            .where(Subscription.status == "active")
            .group_by(Subscription.plan)
        )
        users_by_plan = {row[0]: row[1] for row in users_by_plan_result.all()}
        
        revenue_by_plan = {
            "free": Decimal(0),
            "pro": Decimal(users_by_plan.get("pro", 0) * 29.90)
        }
        
        return MetricsResponse(
            mrr=mrr,
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            total_revenue=Decimal(total_revenue),
            churn_rate=churn_rate,
            transactions_count=transactions_count,
            avg_transaction_value=Decimal(avg_transaction_value),
            users_by_plan=users_by_plan,
            revenue_by_plan=revenue_by_plan
        )
    
    except Exception as e:
        logger.error(f"Error getting admin metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving metrics"
        )


@router.get("/funnel", response_model=FunnelMetrics)
async def get_funnel_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    try:
        analytics_service = AnalyticsService(db)
        return await analytics_service.get_funnel_metrics()
    except Exception as e:
        logger.error(f"Error getting funnel metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving funnel metrics"
        )


@router.get("/retention-cohort", response_model=CohortMetrics)
async def get_retention_cohort(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    try:
        analytics_service = AnalyticsService(db)
        return await analytics_service.get_cohort_retention()
    except Exception as e:
        logger.error(f"Error getting cohort metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving cohort metrics"
        )


@router.get("/conversion", response_model=ConversionMetrics)
async def get_conversion_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    try:
        analytics_service = AnalyticsService(db)
        return await analytics_service.get_conversion_rate()
    except Exception as e:
        logger.error(f"Error getting conversion metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversion metrics"
        )


@router.get("/retention", response_model=RetentionMetrics)
async def get_retention_metrics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    try:
        analytics_service = AnalyticsService(db)
        return await analytics_service.get_retention_rate(days)
    except Exception as e:
        logger.error(f"Error getting retention metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving retention metrics"
        )


@router.get("/churn", response_model=ChurnMetrics)
async def get_churn_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    try:
        analytics_service = AnalyticsService(db)
        return await analytics_service.get_churn_rate()
    except Exception as e:
        logger.error(f"Error getting churn metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving churn metrics"
        )


@router.get("/ltv", response_model=LTVMetrics)
async def get_ltv_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    try:
        analytics_service = AnalyticsService(db)
        return await analytics_service.get_ltv_estimate()
    except Exception as e:
        logger.error(f"Error getting LTV metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving LTV metrics"
        )


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_admin_dashboard(
    cac_estimate: float = Query(50.0, description="Estimated Customer Acquisition Cost"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    try:
        analytics_service = AnalyticsService(db)
        
        active_subs_result = await db.execute(
            select(func.count(Subscription.id))
            .where(Subscription.status == "active")
        )
        active_subscriptions = active_subs_result.scalar_one()
        
        mrr = active_subscriptions * 29.90
        
        total_revenue_result = await db.execute(
            select(func.coalesce(func.sum(PaymentEvent.amount), 0))
            .where(
                and_(
                    PaymentEvent.status == "approved",
                    PaymentEvent.amount.isnot(None)
                )
            )
        )
        total_revenue = total_revenue_result.scalar_one()
        
        today = datetime.now().date()
        new_users_today_result = await db.execute(
            select(func.count(User.id))
            .where(func.date(User.created_at) == today)
        )
        new_users_today = new_users_today_result.scalar_one()
        
        week_start = datetime.now() - timedelta(days=7)
        new_users_week_result = await db.execute(
            select(func.count(User.id))
            .where(User.created_at >= week_start)
        )
        new_users_this_week = new_users_week_result.scalar_one()
        
        month_start = datetime(datetime.now().year, datetime.now().month, 1)
        new_users_month_result = await db.execute(
            select(func.count(User.id))
            .where(User.created_at >= month_start)
        )
        new_users_this_month = new_users_month_result.scalar_one()
        
        conversion_data = await analytics_service.get_conversion_rate()
        churn_data = await analytics_service.get_churn_rate()
        ltv_data = await analytics_service.get_ltv_estimate()
        
        total_transactions_result = await db.execute(
            select(func.count(Transaction.id))
        )
        total_transactions = total_transactions_result.scalar_one()
        
        return DashboardMetrics(
            mrr=float(mrr),
            total_revenue=float(total_revenue),
            new_users_today=new_users_today,
            new_users_this_week=new_users_this_week,
            new_users_this_month=new_users_this_month,
            conversion_rate=conversion_data["conversion_rate"],
            churn_rate=churn_data["churn_rate"],
            estimated_ltv=ltv_data["estimated_ltv"],
            cac_estimate=cac_estimate,
            active_subscriptions=active_subscriptions,
            total_transactions=total_transactions
        )
    except Exception as e:
        logger.error(f"Error getting admin dashboard: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving dashboard metrics"
        )


@router.post("/fix-phone-numbers")
async def fix_phone_numbers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Normaliza todos os números de telefone para formato Twilio (+5521XXXXXXXXX)"""
    try:
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        updated_count = 0
        updates = []
        
        for user in users:
            original_phone = user.phone_number
            # Remove caracteres não numéricos exceto +
            cleaned = re.sub(r'[^\d+]', '', original_phone)
            
            # Se não tem +, assume Brasil e adiciona +55
            if not cleaned.startswith('+'):
                if cleaned.startswith('0'):
                    cleaned = cleaned[1:]
                cleaned = f'+55{cleaned}'
            
            if original_phone != cleaned:
                logger.info(f"Updating user {user.id} ({user.email}): {original_phone} -> {cleaned}")
                user.phone_number = cleaned
                updated_count += 1
                updates.append({
                    "user_id": user.id,
                    "email": user.email,
                    "old_phone": original_phone,
                    "new_phone": cleaned
                })
        
        if updated_count > 0:
            await db.commit()
            logger.info(f"Successfully updated {updated_count} phone numbers")
        
        return {
            "success": True,
            "updated_count": updated_count,
            "total_users": len(users),
            "updates": updates
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error fixing phone numbers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fixing phone numbers: {str(e)}"
        )
