from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from app.services.saas_billing_service import SaaSBillingService
from app.models.billing import SubscriptionPlan


class EntitlementsService:
    """Service for checking plan-based entitlements and usage limits.

    This service checks whether an organization can perform an action
    based on its current plan and usage counters.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.billing = SaaSBillingService(db)

    async def _get_plan_and_usage(
        self, organization_id: int
    ) -> tuple[Optional[SubscriptionPlan], Optional[Dict[str, Any]]]:
        plan = await self.billing.get_current_plan(organization_id)
        usage = await self.billing.get_usage(organization_id)
        usage_dict = {
            "charges_created": usage.charges_created if usage else 0,
            "customers_created": usage.customers_created if usage else 0,
            "templates_created": usage.templates_created if usage else 0,
            "recurring_tasks_created": usage.recurring_tasks_created if usage else 0,
            "ocr_documents_analyzed": usage.ocr_documents_analyzed if usage else 0,
            "pdf_exports_generated": usage.pdf_exports_generated if usage else 0,
            "whatsapp_messages_processed": usage.whatsapp_messages_processed if usage else 0,
            "collection_followups_generated": usage.collection_followups_generated if usage else 0,
        }
        return plan, usage_dict

    def _allowed_response(self, plan: SubscriptionPlan, feature: str = "") -> Dict[str, Any]:
        return {"allowed": True, "plan": plan.code, "plan_name": plan.name, "feature": feature}

    def _denied_response(
        self, plan: SubscriptionPlan, reason: str, limit: int, current_usage: int, feature: str = ""
    ) -> Dict[str, Any]:
        return {
            "allowed": False,
            "reason": reason,
            "limit": limit,
            "current_usage": current_usage,
            "plan": plan.code,
            "plan_name": plan.name,
            "feature": feature,
        }

    def _feature_denied_response(
        self, plan: SubscriptionPlan, reason: str, feature: str
    ) -> Dict[str, Any]:
        return {
            "allowed": False,
            "reason": reason,
            "plan": plan.code,
            "plan_name": plan.name,
            "feature": feature,
        }

    async def can_create_charge(self, organization_id: int) -> Dict[str, Any]:
        plan, usage = await self._get_plan_and_usage(organization_id)
        if not plan:
            return {"allowed": False, "reason": "no_plan_found", "plan": "none", "feature": "charges"}
        current = usage["charges_created"]
        limit = plan.max_charges_per_month
        if current >= limit:
            return self._denied_response(plan, "monthly_charge_limit_reached", limit, current, "charges")
        return self._allowed_response(plan, "charges")

    async def can_create_customer(self, organization_id: int) -> Dict[str, Any]:
        plan, usage = await self._get_plan_and_usage(organization_id)
        if not plan:
            return {"allowed": False, "reason": "no_plan_found", "plan": "none", "feature": "customers"}
        current = usage["customers_created"]
        limit = plan.max_customers
        if current >= limit:
            return self._denied_response(plan, "customer_limit_reached", limit, current, "customers")
        return self._allowed_response(plan, "customers")

    async def can_create_template(self, organization_id: int) -> Dict[str, Any]:
        plan, usage = await self._get_plan_and_usage(organization_id)
        if not plan:
            return {"allowed": False, "reason": "no_plan_found", "plan": "none", "feature": "templates"}
        current = usage["templates_created"]
        limit = plan.max_message_templates
        if current >= limit:
            return self._denied_response(plan, "template_limit_reached", limit, current, "templates")
        return self._allowed_response(plan, "templates")

    async def can_create_recurring_task(self, organization_id: int) -> Dict[str, Any]:
        plan, usage = await self._get_plan_and_usage(organization_id)
        if not plan:
            return {"allowed": False, "reason": "no_plan_found", "plan": "none", "feature": "recurring_tasks"}
        current = usage["recurring_tasks_created"]
        limit = plan.max_recurring_tasks
        if current >= limit:
            return self._denied_response(plan, "recurring_task_limit_reached", limit, current, "recurring_tasks")
        return self._allowed_response(plan, "recurring_tasks")

    async def can_use_ocr(self, organization_id: int) -> Dict[str, Any]:
        plan, usage = await self._get_plan_and_usage(organization_id)
        if not plan:
            return {"allowed": False, "reason": "no_plan_found", "plan": "none", "feature": "ocr"}
        if not plan.allow_ocr:
            return self._feature_denied_response(plan, "ocr_not_included", "ocr")
        return self._allowed_response(plan, "ocr")

    async def can_export_pdf(self, organization_id: int) -> Dict[str, Any]:
        plan, usage = await self._get_plan_and_usage(organization_id)
        if not plan:
            return {"allowed": False, "reason": "no_plan_found", "plan": "none", "feature": "pdf_export"}
        if not plan.allow_pdf_export:
            return self._feature_denied_response(plan, "pdf_export_not_included", "pdf_export")
        return self._allowed_response(plan, "pdf_export")

    async def can_use_advanced_analytics(self, organization_id: int) -> Dict[str, Any]:
        plan, usage = await self._get_plan_and_usage(organization_id)
        if not plan:
            return {"allowed": False, "reason": "no_plan_found", "plan": "none", "feature": "advanced_analytics"}
        if not plan.allow_advanced_analytics:
            return self._feature_denied_response(plan, "advanced_analytics_not_included", "advanced_analytics")
        return self._allowed_response(plan, "advanced_analytics")

    async def can_use_collection_rules(self, organization_id: int) -> Dict[str, Any]:
        plan, usage = await self._get_plan_and_usage(organization_id)
        if not plan:
            return {"allowed": False, "reason": "no_plan_found", "plan": "none", "feature": "collection_rules"}
        if not plan.allow_collection_rules:
            return self._feature_denied_response(plan, "collection_rules_not_included", "collection_rules")
        return self._allowed_response(plan, "collection_rules")

    async def can_add_team_member(self, organization_id: int) -> Dict[str, Any]:
        plan, usage = await self._get_plan_and_usage(organization_id)
        if not plan:
            return {"allowed": False, "reason": "no_plan_found", "plan": "none", "feature": "team_members"}
        from sqlalchemy import select, func
        from app.models.organization import OrganizationMember
        result = await self.db.execute(
            select(func.count(OrganizationMember.id)).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.active == True,
            )
        )
        current_members = result.scalar() or 0
        limit = plan.max_team_members
        if current_members >= limit:
            return self._denied_response(plan, "team_member_limit_reached", limit, current_members, "team_members")
        return self._allowed_response(plan, "team_members")

    async def can_process_whatsapp_message(self, organization_id: int) -> Dict[str, Any]:
        plan, usage = await self._get_plan_and_usage(organization_id)
        if not plan:
            return {"allowed": False, "reason": "no_plan_found", "plan": "none", "feature": "whatsapp_messages"}
        current = usage["whatsapp_messages_processed"]
        limit = plan.max_whatsapp_messages_per_month
        if limit is not None and current >= limit:
            return self._denied_response(plan, "whatsapp_message_limit_reached", limit, current, "whatsapp_messages")
        return self._allowed_response(plan, "whatsapp_messages")
