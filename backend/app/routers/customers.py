from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.utils.dependencies import get_current_active_user, get_current_organization
from app.services.customer_service import CustomerService
from app.schemas.customer import (
    CustomerListResponse,
    CustomerSummaryResponse,
    CustomerDetailResponse,
    CustomerNotesUpdate,
)
from app.models.user import User
from app.models.organization import Organization

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    search: Optional[str] = Query(None, description="Search by name or phone"),
    status_filter: Optional[str] = Query(None, description="Filter by operational status"),
    has_overdue: Optional[bool] = Query(None, description="Filter customers with overdue charges"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """List customers for the authenticated user with pagination and filters."""
    service = CustomerService(db)
    result = await service.list_customers(
        user_id=current_user.id,
        search=search,
        status_filter=status_filter,
        has_overdue=has_overdue,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        organization_id=org.id,
    )
    return result


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
async def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Get customer detail with charges history."""
    service = CustomerService(db)
    detail = await service.get_customer_detail(customer_id, current_user.id, organization_id=org.id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return detail


@router.get("/{customer_id}/charges")
async def get_customer_charges(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Get all charges for a specific customer."""
    service = CustomerService(db)
    charges = await service.get_customer_charges(customer_id, current_user.id, organization_id=org.id)
    if not charges:
        customer = await service.get_customer(customer_id, current_user.id, organization_id=org.id)
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return {
        "items": [
            {
                "id": c.id,
                "amount": float(c.amount),
                "description": c.description,
                "status": c.status.value,
                "due_date": c.due_date.isoformat() if c.due_date else None,
                "paid_at": c.paid_at.isoformat() if c.paid_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "payment_link": c.payment_link,
            }
            for c in charges
        ],
        "total": len(charges),
    }


@router.get("/{customer_id}/summary", response_model=CustomerSummaryResponse)
async def get_customer_summary(
    customer_id: int,
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Get operational summary for a customer."""
    service = CustomerService(db)
    customer = await service.get_customer(customer_id, current_user.id, organization_id=org.id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    summary = await service.get_customer_summary(customer, current_user.id, organization_id=org.id)
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "notes": customer.notes,
        **summary,
    }


@router.patch("/{customer_id}/notes")
async def update_customer_notes(
    customer_id: int,
    data: CustomerNotesUpdate,
    current_user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Update customer notes."""
    service = CustomerService(db)
    customer = await service.update_customer_notes(customer_id, current_user.id, data.notes, organization_id=org.id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return {"id": customer.id, "notes": customer.notes}
