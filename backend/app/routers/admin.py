from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract, text
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List
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
from app.models.charge import Charge, ChargeStatus
from app.models.provider_event import ProviderEvent
from app.models.charge_reminder_log import ChargeReminderLog
from app.models.charge_delivery_log import ChargeDeliveryLog
from app.core.logging import logger
from app.utils.dependencies import get_current_admin_user
import re
import time as time_module

router = APIRouter(prefix="/admin", tags=["Admin"])

_start_time = time_module.time()

ORG_SCOPED_TABLES = [
    "charges",
    "customers",
    "message_templates",
    "collection_rules",
    "collection_message_logs",
    "recurring_tasks",
    "pending_actions",
]


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


@router.get("/system-metrics")
async def get_system_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Return system-level metrics: charges, webhooks, reminders, delivery logs.
    No personal data or financial values per user are exposed.
    """
    try:
        total_users = (await db.execute(select(func.count(User.id)))).scalar_one()

        total_charges = (await db.execute(select(func.count(Charge.id)))).scalar_one()
        paid_charges = (await db.execute(
            select(func.count(Charge.id)).where(Charge.status == ChargeStatus.PAID)
        )).scalar_one()
        pending_charges = (await db.execute(
            select(func.count(Charge.id)).where(Charge.status == ChargeStatus.PENDING)
        )).scalar_one()

        today = date.today()
        overdue_charges = (await db.execute(
            select(func.count(Charge.id)).where(
                Charge.status == ChargeStatus.PENDING,
                Charge.due_date < today
            )
        )).scalar_one()

        total_provider_events = (await db.execute(select(func.count(ProviderEvent.id)))).scalar_one()
        processed_events = (await db.execute(
            select(func.count(ProviderEvent.id)).where(ProviderEvent.processed == True)
        )).scalar_one()

        total_reminders = (await db.execute(select(func.count(ChargeReminderLog.id)))).scalar_one()
        total_delivery_logs = (await db.execute(select(func.count(ChargeDeliveryLog.id)))).scalar_one()

        # Billing metrics
        from app.models.billing import SubscriptionPlan, OrganizationSubscription, UsageCounter
        from app.models.organization import Organization as OrgModel
        total_orgs = (await db.execute(select(func.count(OrgModel.id)))).scalar_one()
        total_subscriptions = (await db.execute(select(func.count(OrganizationSubscription.id)))).scalar_one()
        active_subscriptions = (await db.execute(
            select(func.count(OrganizationSubscription.id)).where(
                OrganizationSubscription.status == "active"
            )
        )).scalar_one()
        trialing_subscriptions = (await db.execute(
            select(func.count(OrganizationSubscription.id)).where(
                OrganizationSubscription.status == "trialing"
            )
        )).scalar_one()
        cancelled_subscriptions = (await db.execute(
            select(func.count(OrganizationSubscription.id)).where(
                OrganizationSubscription.status == "cancelled"
            )
        )).scalar_one()

        # Subscriptions per plan
        plan_counts_result = await db.execute(
            select(SubscriptionPlan.code, func.count(OrganizationSubscription.id))
            .outerjoin(OrganizationSubscription, OrganizationSubscription.plan_id == SubscriptionPlan.id)
            .group_by(SubscriptionPlan.code)
        )
        plan_counts = {row[0]: row[1] for row in plan_counts_result.all()}

        # Total usage this period
        total_charges_created_usage = (await db.execute(
            select(func.sum(UsageCounter.charges_created))
        )).scalar() or 0

        uptime_seconds = time_module.time() - _start_time

        return {
            "total_users": total_users,
            "total_charges": total_charges,
            "paid_charges": paid_charges,
            "pending_charges": pending_charges,
            "overdue_charges": overdue_charges,
            "total_provider_events": total_provider_events,
            "processed_provider_events": processed_events,
            "total_reminders_sent": total_reminders,
            "total_delivery_logs": total_delivery_logs,
            "uptime_seconds": round(uptime_seconds, 2),
            "billing": {
                "total_organizations": total_orgs,
                "total_subscriptions": total_subscriptions,
                "active_subscriptions": active_subscriptions,
                "trialing_subscriptions": trialing_subscriptions,
                "cancelled_subscriptions": cancelled_subscriptions,
                "subscriptions_per_plan": plan_counts,
                "total_charges_created_this_period": total_charges_created_usage,
            },
        }

    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving system metrics"
        )


@router.get("/multitenant-health")
async def get_multitenant_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Check multi-tenant integrity: detect orphan records without organization_id."""
    try:
        orphan_records = 0
        null_organization_records = 0

        for table in ORG_SCOPED_TABLES:
            null_count = (await db.execute(text(
                f"SELECT COUNT(*) FROM {table} WHERE organization_id IS NULL"
            ))).scalar()
            invalid_count = (await db.execute(text(
                f"SELECT COUNT(*) FROM {table} t "
                f"WHERE t.organization_id IS NOT NULL "
                f"AND NOT EXISTS (SELECT 1 FROM organizations o WHERE o.id = t.organization_id)"
            ))).scalar()

            null_organization_records += null_count
            orphan_records += null_count + invalid_count

        return {
            "status": "ok" if orphan_records == 0 else "warning",
            "tables_checked": len(ORG_SCOPED_TABLES),
            "orphan_records": orphan_records,
            "null_organization_records": null_organization_records,
        }

    except Exception as e:
        logger.error(f"Error checking multi-tenant health: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking multi-tenant health"
        )


@router.get("/billing-metrics")
async def get_billing_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get aggregated SaaS billing metrics: subs by status, orgs by plan, usage totals."""
    try:
        from app.models.billing import (
            OrganizationSubscription, SubscriptionPlan, UsageCounter, SubscriptionStatus
        )

        # Subscriptions by status
        status_counts = {}
        for s in SubscriptionStatus:
            count = (await db.execute(
                select(func.count(OrganizationSubscription.id)).where(
                    OrganizationSubscription.status == s
                )
            )).scalar()
            status_counts[s.value] = count

        # Organizations by plan
        plan_counts = await db.execute(
            select(
                SubscriptionPlan.code,
                SubscriptionPlan.name,
                func.count(OrganizationSubscription.id)
            ).join(
                OrganizationSubscription, OrganizationSubscription.plan_id == SubscriptionPlan.id
            ).group_by(SubscriptionPlan.code, SubscriptionPlan.name)
        )
        orgs_by_plan = [
            {"plan_code": row[0], "plan_name": row[1], "count": row[2]}
            for row in plan_counts
        ]

        # Total usage across all orgs (current period)
        usage_totals = await db.execute(
            select(
                func.coalesce(func.sum(UsageCounter.charges_created), 0).label("total_charges"),
                func.coalesce(func.sum(UsageCounter.customers_created), 0).label("total_customers"),
                func.coalesce(func.sum(UsageCounter.templates_created), 0).label("total_templates"),
                func.coalesce(func.sum(UsageCounter.recurring_tasks_created), 0).label("total_recurring_tasks"),
                func.coalesce(func.sum(UsageCounter.ocr_documents_analyzed), 0).label("total_ocr"),
                func.coalesce(func.sum(UsageCounter.pdf_exports_generated), 0).label("total_pdf_exports"),
                func.coalesce(func.sum(UsageCounter.whatsapp_messages_processed), 0).label("total_whatsapp_messages"),
                func.coalesce(func.sum(UsageCounter.collection_followups_generated), 0).label("total_followups"),
            )
        )
        row = usage_totals.one()
        usage = {
            "total_charges": row.total_charges,
            "total_customers": row.total_customers,
            "total_templates": row.total_templates,
            "total_recurring_tasks": row.total_recurring_tasks,
            "total_ocr_documents": row.total_ocr,
            "total_pdf_exports": row.total_pdf_exports,
            "total_whatsapp_messages": row.total_whatsapp_messages,
            "total_collection_followups": row.total_followups,
        }

        # Total billing events
        total_events = (await db.execute(
            select(func.count(text("1"))).select_from(text("billing_events"))
        )).scalar()

        # Provider foundation metrics
        from app.models.provider_foundation import (
            ProviderConnection, ProviderWebhookEvent,
            OpenFinanceConsent, OrganizationAuditLog,
            TransactionAuthorization, ProviderConnectionStatus,
            WebhookEventStatus, ConsentStatus, AuthorizationStatus,
        )

        connections_total = (await db.execute(
            select(func.count(ProviderConnection.id))
        )).scalar()
        connections_active = (await db.execute(
            select(func.count(ProviderConnection.id)).where(
                ProviderConnection.active == True,
                ProviderConnection.status == ProviderConnectionStatus.ACTIVE,
            )
        )).scalar()

        of_consents_by_status = {}
        for s in ConsentStatus:
            c = (await db.execute(
                select(func.count(OpenFinanceConsent.id)).where(
                    OpenFinanceConsent.status == s
                )
            )).scalar()
            of_consents_by_status[s.value] = c

        webhook_events_by_status = {}
        for s in WebhookEventStatus:
            c = (await db.execute(
                select(func.count(ProviderWebhookEvent.id)).where(
                    ProviderWebhookEvent.status == s
                )
            )).scalar()
            webhook_events_by_status[s.value] = c

        tx_auths_by_status = {}
        for s in AuthorizationStatus:
            c = (await db.execute(
                select(func.count(TransactionAuthorization.id)).where(
                    TransactionAuthorization.status == s
                )
            )).scalar()
            tx_auths_by_status[s.value] = c

        audit_logs_total = (await db.execute(
            select(func.count(OrganizationAuditLog.id))
        )).scalar()

        provider_metrics = {
            "connections_total": connections_total,
            "connections_active": connections_active,
            "of_consents_by_status": of_consents_by_status,
            "webhook_events_by_status": webhook_events_by_status,
            "tx_auths_by_status": tx_auths_by_status,
            "audit_logs_total": audit_logs_total,
        }

        # Open Finance read metrics — Sprint 16
        from app.models.open_finance import (
            ConnectedAccount, BankTransaction, OpenFinanceSyncLog,
            ConnectedAccountStatus, SyncStatus,
        )
        of_accounts_total = (await db.execute(
            select(func.count(ConnectedAccount.id))
        )).scalar()
        of_accounts_active = (await db.execute(
            select(func.count(ConnectedAccount.id)).where(
                ConnectedAccount.status == ConnectedAccountStatus.ACTIVE
            )
        )).scalar()
        of_demo_accounts = (await db.execute(
            select(func.count(ConnectedAccount.id)).where(
                ConnectedAccount.is_demo_data == True
            )
        )).scalar()
        of_transactions_total = (await db.execute(
            select(func.count(BankTransaction.id))
        )).scalar()
        of_demo_transactions = (await db.execute(
            select(func.count(BankTransaction.id)).where(
                BankTransaction.is_demo_data == True
            )
        )).scalar()
        of_sync_logs_by_status = {}
        for s in SyncStatus:
            c = (await db.execute(
                select(func.count(OpenFinanceSyncLog.id)).where(
                    OpenFinanceSyncLog.status == s
                )
            )).scalar()
            of_sync_logs_by_status[s.value] = c

        open_finance_metrics = {
            "connected_accounts_total": of_accounts_total,
            "connected_accounts_active": of_accounts_active,
            "connected_accounts_demo": of_demo_accounts,
            "bank_transactions_total": of_transactions_total,
            "bank_transactions_demo": of_demo_transactions,
            "sync_logs_by_status": of_sync_logs_by_status,
        }

        # Bill management metrics — Sprint 17
        from app.models.bills import (
            DetectedBill, BillReminder, BillPaymentIntent, BillEventLog,
            BillStatus, BillReminderStatus, PaymentIntentStatus,
        )
        bills_total = (await db.execute(
            select(func.count(DetectedBill.id))
        )).scalar()
        bills_overdue = (await db.execute(
            select(func.count(DetectedBill.id)).where(
                DetectedBill.status == BillStatus.OVERDUE
            )
        )).scalar()
        bills_due_today = (await db.execute(
            select(func.count(DetectedBill.id)).where(
                DetectedBill.status == BillStatus.DUE_TODAY
            )
        )).scalar()
        fake_payment_intents_by_status = {}
        for s in PaymentIntentStatus:
            c = (await db.execute(
                select(func.count(BillPaymentIntent.id)).where(
                    BillPaymentIntent.status == s
                )
            )).scalar()
            fake_payment_intents_by_status[s.value] = c
        reminders_by_status = {}
        for s in BillReminderStatus:
            c = (await db.execute(
                select(func.count(BillReminder.id)).where(
                    BillReminder.status == s
                )
            )).scalar()
            reminders_by_status[s.value] = c
        bill_event_logs_total = (await db.execute(
            select(func.count(BillEventLog.id))
        )).scalar()

        bill_metrics = {
            "detected_bills_total": bills_total,
            "bills_overdue": bills_overdue,
            "bills_due_today": bills_due_today,
            "fake_payment_intents_by_status": fake_payment_intents_by_status,
            "reminders_by_status": reminders_by_status,
            "bill_event_logs_total": bill_event_logs_total,
        }

        return {
            "subscriptions_by_status": status_counts,
            "organizations_by_plan": orgs_by_plan,
            "usage_totals": usage,
            "total_billing_events": total_events,
            "provider_connections_total": provider_metrics["connections_total"],
            "provider_connections_active": provider_metrics["connections_active"],
            "open_finance_consents_by_status": provider_metrics["of_consents_by_status"],
            "webhook_events_by_status": provider_metrics["webhook_events_by_status"],
            "transaction_authorizations_by_status": provider_metrics["tx_auths_by_status"],
            "audit_logs_total": provider_metrics["audit_logs_total"],
            "open_finance_connected_accounts_total": open_finance_metrics["connected_accounts_total"],
            "open_finance_connected_accounts_active": open_finance_metrics["connected_accounts_active"],
            "open_finance_connected_accounts_demo": open_finance_metrics["connected_accounts_demo"],
            "open_finance_bank_transactions_total": open_finance_metrics["bank_transactions_total"],
            "open_finance_bank_transactions_demo": open_finance_metrics["bank_transactions_demo"],
            "open_finance_sync_logs_by_status": open_finance_metrics["sync_logs_by_status"],
            "detected_bills_total": bill_metrics["detected_bills_total"],
            "bills_overdue": bill_metrics["bills_overdue"],
            "bills_due_today": bill_metrics["bills_due_today"],
            "fake_payment_intents_by_status": bill_metrics["fake_payment_intents_by_status"],
            "bill_reminders_by_status": bill_metrics["reminders_by_status"],
            "bill_event_logs_total": bill_metrics["bill_event_logs_total"],
        }

    except Exception as e:
        logger.error(f"Error getting billing metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting billing metrics"
        )
